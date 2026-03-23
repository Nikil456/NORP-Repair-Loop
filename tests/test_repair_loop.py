import pytest
from unittest.mock import Mock, AsyncMock
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
