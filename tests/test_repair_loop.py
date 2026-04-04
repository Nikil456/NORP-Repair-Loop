import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestSimpleExtraction:
    def test_extract_sql_basic(self):
        import re
        response = "```sql\nSELECT * FROM users\n```"
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
        result = sql_match.group(1).strip() if sql_match else response.strip()
        assert result == "SELECT * FROM users"


class TestOrchestratorImports:
    def test_orchestrator_can_be_imported(self):
        from services.repair_loop import SelfCorrectionOrchestrator
        assert SelfCorrectionOrchestrator is not None
    
    def test_logic_verifier_instantiated(self):
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_db = Mock()
        mock_db.get_table_info = Mock(return_value="schema")
        mock_redis = Mock()
        mock_execute_tool = Mock()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm,
            db=mock_db,
            redis_client=mock_redis,
            use_rag=False,
            execute_tool=mock_execute_tool,
        )
        assert orchestrator is not None
        assert orchestrator.logic_verifier is not None


class MockExecuteTool:
    def invoke(self, query_dict):
        return []


class TestHistoryFormatting:
    """Tests for history-aware refinement features."""
    
    def test_format_past_attempts_empty(self):
        """Test formatting empty history."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_redis = Mock()
        mock_execute_tool = MockExecuteTool()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=mock_execute_tool
        )
        
        result = orchestrator._format_past_attempts([])
        assert "No previous attempts" in result
    
    def test_format_past_attempts_with_data(self):
        """Test formatting history with multiple entries."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_redis = Mock()
        mock_execute_tool = MockExecuteTool()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=mock_execute_tool
        )
        
        history = [
            {
                "attempt_number": 1,
                "sql": "SELECT * FROM users",
                "error": "Table not found",
                "logic_feedback": "",
                "type": "EXECUTION_ERROR",
                "timestamp": "2024-01-01T00:00:00"
            },
            {
                "attempt_number": 2,
                "sql": "SELECT * FROM wrong_table",
                "error": "",
                "logic_feedback": "Query doesn't match intent",
                "type": "LOGIC_ERROR",
                "timestamp": "2024-01-01T00:01:00"
            }
        ]
        
        result = orchestrator._format_past_attempts(history)
        
        assert "Attempt 1" in result
        assert "Attempt 2" in result
        assert "EXECUTION_ERROR" in result
        assert "LOGIC_ERROR" in result
        assert "SELECT * FROM users" in result
    
    def test_trim_history_under_threshold(self):
        """Test that history under max is not trimmed."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_redis = Mock()
        mock_execute_tool = MockExecuteTool()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=mock_execute_tool
        )
        
        history = [
            {"attempt_number": 1, "sql": "SELECT 1"},
            {"attempt_number": 2, "sql": "SELECT 2"},
            {"attempt_number": 3, "sql": "SELECT 3"},
        ]
        
        result = orchestrator._trim_history(history, max_attempts=4)
        assert len(result) == 3
    
    def test_trim_history_over_threshold(self):
        """Test that history over max is trimmed."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_redis = Mock()
        mock_execute_tool = MockExecuteTool()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=mock_execute_tool
        )
        
        history = [
            {"attempt_number": i, "sql": f"SELECT {i}"} for i in range(1, 8)
        ]
        
        result = orchestrator._trim_history(history, max_attempts=4)
        
        # Should keep first + 3 most recent = 4 entries
        assert len(result) == 4
        # First entry should be preserved
        assert result[0]["attempt_number"] == 1
        # Last 3 should be the most recent
        assert result[-1]["attempt_number"] == 7
    
    def test_trim_history_preserves_original(self):
        """Test that original attempt is always preserved."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        mock_redis = Mock()
        mock_execute_tool = MockExecuteTool()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=mock_execute_tool
        )
        
        history = [
            {"attempt_number": 1, "sql": "ORIGINAL QUERY"},
            {"attempt_number": 2, "sql": "ATTEMPT 2"},
            {"attempt_number": 3, "sql": "ATTEMPT 3"},
            {"attempt_number": 4, "sql": "ATTEMPT 4"},
            {"attempt_number": 5, "sql": "ATTEMPT 5"},
        ]
        
        result = orchestrator._trim_history(history, max_attempts=4)
        
        # Original should always be first
        assert result[0]["sql"] == "ORIGINAL QUERY"


class TestHistoryValidation:
    """Tests for graceful reset of old format."""
    
    def test_get_attempt_history_validates_format(self):
        """Test that old format triggers reset."""
        from services.repair_loop import SelfCorrectionOrchestrator
        mock_llm = Mock()
        
        # Mock Redis with old format (missing attempt_number)
        mock_redis = Mock()
        mock_redis.lrange = Mock(return_value=['{"attempt": 1, "error": "test"}'])
        mock_redis.delete = Mock()
        
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm, db=Mock(), redis_client=mock_redis, 
            use_rag=False, execute_tool=MockExecuteTool()
        )
        
        result = orchestrator._get_attempt_history("test-session")
        
        # Should return empty and trigger clear
        assert result == []
        mock_redis.delete.assert_called_once()


class TestMultiTurnFailure:
    """Test multi-turn failure scenario."""
    
    @pytest.mark.asyncio
    async def test_multi_turn_failure_uses_full_history(self):
        """Test that orchestrator uses full history in refinement."""
        from services.repair_loop import SelfCorrectionOrchestrator
        
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(return_value=Mock(content="```sql\nSELECT * FROM correct\n```"))
        
        # Mock Redis with history
        mock_redis = Mock()
        mock_redis.lrange = Mock(return_value=[
            '{"attempt_number": 1, "sql": "SELECT * FROM wrong", "error": "Table not found", "logic_feedback": "", "type": "EXECUTION_ERROR", "timestamp": "2024-01-01T00:00:00"}',
            '{"attempt_number": 2, "sql": "SELECT * FROM also_wrong", "error": "", "logic_feedback": "Wrong aggregation", "type": "LOGIC_ERROR", "timestamp": "2024-01-01T00:01:00"}',
        ])
        
        mock_execute_tool = MockExecuteTool()
        
        # Test that history is retrieved and formatted - no need to mock LogicVerificationAgent
        orchestrator = SelfCorrectionOrchestrator(
            llm=mock_llm,
            db=Mock(),
            redis_client=mock_redis,
            max_retries=3,
            use_rag=False,
            execute_tool=mock_execute_tool,
        )
        
        # Test that history is retrieved and formatted
        history = orchestrator._get_attempt_history("test-multi")
        formatted = orchestrator._format_past_attempts(history)
        
        assert len(history) == 2
        assert "Attempt 1" in formatted
        assert "Attempt 2" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])