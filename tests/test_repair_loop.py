import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict, List
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.repair_loop.SelfCorrectionOrchestrator import SelfCorrectionOrchestrator
from services.repair_loop.verification_agent import logic_verification_agent


class MockRedis:
    def __init__(self):
        self.data = {}
    
    def lrange(self, key, start, end):
        return self.data.get(key, [])
    
    def rpush(self, key, value):
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)
    
    def expire(self, key, ttl):
        pass


class MockExecuteTool:
    def __init__(self, side_effect=None, return_value=None):
        self._side_effect = side_effect
        self._return_value = return_value
    
    def invoke(self, query_dict):
        if self._side_effect:
            if callable(self._side_effect):
                return self._side_effect(query_dict)
            raise self._side_effect
        return self._return_value


@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_db():
    db = Mock()
    db.get_table_info = Mock(return_value="Table: users\nColumns: id, name, email")
    return db


@pytest.fixture
def mock_redis():
    return MockRedis()


class TestSQLExtration:
    """Test SQL extraction from LLM responses."""
    
    def test_extract_sql_from_code_block(self):
        mock_execute_tool = Mock()
        orchestrator = SelfCorrectionOrchestrator(
            llm=None,
            db=None,
            redis_client=None,
            execute_tool=mock_execute_tool,
        )
        
        result = orchestrator._extract_sql_from_response(
            "```sql\nSELECT * FROM users\n```"
        )
        assert result == "SELECT * FROM users"
    
    def test_extract_sql_from_markdown_response(self):
        mock_execute_tool = Mock()
        orchestrator = SelfCorrectionOrchestrator(
            llm=None,
            db=None,
            redis_client=None,
            execute_tool=mock_execute_tool,
        )
        
        result = orchestrator._extract_sql_from_response(
            "Here is your query:\n```sql\nSELECT id, name FROM users WHERE active = 1\n```"
        )
        assert result == "SELECT id, name FROM users WHERE active = 1"
    
    def test_extract_sql_plain_text(self):
        mock_execute_tool = Mock()
        orchestrator = SelfCorrectionOrchestrator(
            llm=None,
            db=None,
            redis_client=None,
            execute_tool=mock_execute_tool,
        )
        
        result = orchestrator._extract_sql_from_response(
            "SELECT * FROM users"
        )
        assert result == "SELECT * FROM users"


class TestLogicVerificationAgentStub:
    """Test the verification agent stub."""
    
    @pytest.mark.asyncio
    async def test_stub_returns_valid(self):
        result = await logic_verification_agent(
            sql="SELECT * FROM users",
            results=[{"id": 1}],
            question="Get all users"
        )
        
        assert result["is_valid"] is True
        assert result["feedback"] is None


class TestRedisHistoryStorage:
    """Test Redis history storage via direct orchestrator methods."""
    
    def test_format_history_empty(self):
        mock_execute_tool = Mock()
        orchestrator = SelfCorrectionOrchestrator(
            llm=None,
            db=None,
            redis_client=None,
            execute_tool=mock_execute_tool,
        )
        
        result = orchestrator._format_history_for_prompt([])
        assert "No previous attempts" in result
    
    def test_format_history_with_attempts(self):
        mock_execute_tool = Mock()
        orchestrator = SelfCorrectionOrchestrator(
            llm=None,
            db=None,
            redis_client=None,
            execute_tool=mock_execute_tool,
        )
        
        history = [
            {"attempt": 1, "error": "Table not found", "sql": "SELECT * FROM users", "type": "EXECUTION_ERROR"},
            {"attempt": 2, "error": "Column missing", "sql": "SELECT id FROM users", "type": "LOGIC_ERROR"},
        ]
        
        result = orchestrator._format_history_for_prompt(history)
        assert "Attempt 1" in result
        assert "Attempt 2" in result
        assert "EXECUTION_ERROR" in result
        assert "LOGIC_ERROR" in result


class TestOrchestratorStateMachine:
    """Test the orchestrator's state machine logic with mocks."""
    
    @pytest.mark.asyncio
    async def test_syntax_error_triggers_single_retry(self, mock_llm, mock_db, mock_redis):
        call_count = [0]
        
        async def mock_invoke(prompt):
            call_count[0] += 1
            mock_response = Mock()
            if call_count[0] == 1:
                mock_response.content = "```sql\nSELECT * FROM users\n```"
            else:
                mock_response.content = "```sql\nSELECT id, name FROM users\n```"
            return mock_response
        
        mock_llm.ainvoke = mock_invoke
        
        execute_count = [0]
        def mock_execute(query_dict):
            execute_count[0] += 1
            if execute_count[0] == 1:
                raise Exception("Syntax error: Table 'userss' doesn't exist")
            return [{"id": 1, "name": "John"}]
        
        mock_execute_tool = MockExecuteTool(side_effect=mock_execute)
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm,
            db=mock_db,
            redis_client=mock_redis,
            max_retries=3,
            use_rag=False,
            execute_tool=mock_execute_tool,
        )
        
        result = await orchestrator.execute(
            question="Get all users",
            session_id="test_session_1"
        )
        
        assert result["success"] is True
        assert result["attempts"] == 2
        assert call_count[0] == 2
    
    @pytest.mark.asyncio
    async def test_logic_failure_triggers_retry(self, mock_llm, mock_db, mock_redis):
        call_count = [0]
        
        async def mock_invoke(prompt):
            call_count[0] += 1
            mock_response = Mock()
            if call_count[0] == 1:
                mock_response.content = "```sql\nSELECT id FROM users\n```"
            else:
                mock_response.content = "```sql\nSELECT id, name FROM users\n```"
            return mock_response
        
        mock_llm.ainvoke = mock_invoke
        
        mock_execute_tool = MockExecuteTool(return_value=[{"id": 1}])
        
        verification_calls = [0]
        async def mock_verify(sql, results, question):
            verification_calls[0] += 1
            if verification_calls[0] == 1:
                return {"is_valid": False, "feedback": "Query doesn't include name column"}
            return {"is_valid": True, "feedback": None}
        
        import services.repair_loop.verification_agent as verify_module
        original_verify = verify_module.logic_verification_agent
        verify_module.logic_verification_agent = mock_verify
        
        try:
            orchestrator = SelfCorrectionOrchestrator(
                llm=mock_llm,
                db=mock_db,
                redis_client=mock_redis,
                max_retries=3,
                use_rag=False,
                execute_tool=mock_execute_tool,
            )
            
            result = await orchestrator.execute(
                question="Get all users",
                session_id="test_session_2"
            )
            
            assert result["success"] is True
            assert result["attempts"] == 2
        finally:
            verify_module.logic_verification_agent = original_verify
    
    @pytest.mark.asyncio
    async def test_max_retries_breakpoint(self, mock_llm, mock_db, mock_redis):
        async def mock_invoke(prompt):
            mock_response = Mock()
            mock_response.content = "```sql\nSELECT * FROM invalid_table\n```"
            return mock_response
        
        mock_llm.ainvoke = mock_invoke
        
        mock_execute_tool = MockExecuteTool(
            side_effect=Exception("Table doesn't exist")
        )
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm,
            db=mock_db,
            redis_client=mock_redis,
            max_retries=3,
            use_rag=False,
            execute_tool=mock_execute_tool,
        )
        
        result = await orchestrator.execute(
            question="Get all users",
            session_id="test_session_3"
        )
        
        assert result["success"] is False
        assert result["error"] == "MAX_RETRIES_EXCEEDED"
        assert result["attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_happy_path_no_retries(self, mock_llm, mock_db, mock_redis):
        async def mock_invoke(prompt):
            mock_response = Mock()
            mock_response.content = "```sql\nSELECT id, name FROM users\n```"
            return mock_response
        
        mock_llm.ainvoke = mock_invoke
        
        mock_execute_tool = MockExecuteTool(return_value=[{"id": 1, "name": "John"}])
        
        async def mock_verify(sql, results, question):
            return {"is_valid": True, "feedback": None}
        
        import services.repair_loop.verification_agent as verify_module
        original_verify = verify_module.logic_verification_agent
        verify_module.logic_verification_agent = mock_verify
        
        try:
            orchestrator = SelfCorrectionOrchestrator(
                llm=mock_llm,
                db=mock_db,
                redis_client=mock_redis,
                max_retries=3,
                use_rag=False,
                execute_tool=mock_execute_tool,
            )
            
            result = await orchestrator.execute(
                question="Get all users",
                session_id="test_session_4"
            )
            
            assert result["success"] is True
            assert result["attempts"] == 1
            assert "id" in result["sql_query"]
            assert "name" in result["sql_query"]
        finally:
            verify_module.logic_verification_agent = original_verify


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
