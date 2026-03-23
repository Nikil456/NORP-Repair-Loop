"""
Unit tests for the Logic Verification Agent (Week 10 Deliverable)

Tests the FinStat2SQL Logical Critic implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from auto_correction.logic_verification_agent import LogicVerificationAgent, logic_verification_agent


class TestLogicVerificationAgent:
    """Test suite for LogicVerificationAgent class"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client"""
        return Mock()

    @pytest.fixture
    def agent(self, mock_llm):
        """Create a LogicVerificationAgent instance with mock LLM"""
        return LogicVerificationAgent(mock_llm)

    def test_format_execution_result_none(self, agent):
        """Test formatting None result"""
        result = agent._format_execution_result(None)
        assert result == "[No result]"

    def test_format_execution_result_string(self, agent):
        """Test formatting string result"""
        result = agent._format_execution_result("Query successful")
        assert result == "Query successful"

    def test_format_execution_result_empty_list(self, agent):
        """Test formatting empty list result"""
        result = agent._format_execution_result([])
        assert result == "[Empty result set]"

    def test_format_execution_result_list(self, agent):
        """Test formatting list result with data"""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = agent._format_execution_result(data)
        assert "Row 1:" in result
        assert "Row 2:" in result
        assert "{'id': 1, 'name': 'Alice'}" in result

    def test_format_execution_result_dict(self, agent):
        """Test formatting dict result"""
        data = {"count": 42, "status": "ok"}
        result = agent._format_execution_result(data)
        assert "count:" in result
        assert "status:" in result

    def test_parse_verification_response_yes(self, agent):
        """Test parsing YES decision"""
        response = """
        ### Decision: YES
        ### Reasoning: The query correctly returns all records matching the user's intent.
        """
        matches_intent, reasoning, new_sql = agent._parse_verification_response(response)
        assert matches_intent is True
        assert "correctly returns" in reasoning

    def test_parse_verification_response_no(self, agent):
        """Test parsing NO decision with corrected SQL"""
        response = """
        ### Decision: NO
        ### Reasoning: The query is missing a WHERE clause to filter by age.
        ### SQL Query: SELECT * FROM users WHERE age > 18
        """
        matches_intent, reasoning, new_sql = agent._parse_verification_response(response)
        assert matches_intent is False
        assert "missing a WHERE clause" in reasoning
        assert "SELECT * FROM users WHERE age > 18" in new_sql

    def test_parse_verification_response_with_markdown(self, agent):
        """Test parsing response with markdown code blocks"""
        response = """
        ### Decision: NO
        ### Reasoning: Need to add filtering
        ### SQL Query: ```sql
        SELECT * FROM table WHERE condition=true
        ```
        """
        matches_intent, reasoning, new_sql = agent._parse_verification_response(response)
        assert matches_intent is False
        assert "SELECT * FROM table WHERE condition=true" in new_sql
        assert "```" not in new_sql  # Markdown should be cleaned

    @pytest.mark.asyncio
    async def test_verify_matches_intent(self, agent):
        """Test verification when query matches intent"""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = "### Decision: YES\n### Reasoning: Correct query"
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        matches_intent, new_sql, metadata = await agent.verify(
            current_sql="SELECT * FROM users",
            user_query="Get all users",
            execution_result=[{"id": 1}, {"id": 2}],
        )

        assert matches_intent is True
        assert new_sql == ""
        assert metadata["matches_intent"] is True
        assert "explanation" in metadata

    @pytest.mark.asyncio
    async def test_verify_does_not_match_intent(self, agent):
        """Test verification when query doesn't match intent"""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = """
        ### Decision: NO
        ### Reasoning: Missing WHERE clause
        ### SQL Query: SELECT * FROM users WHERE active=1
        """
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        matches_intent, new_sql, metadata = await agent.verify(
            current_sql="SELECT * FROM users",
            user_query="Get all active users",
            execution_result=[],
        )

        assert matches_intent is False
        assert "SELECT * FROM users WHERE active=1" in new_sql
        assert metadata["matches_intent"] is False
        assert "Missing WHERE clause" in metadata["explanation"]

    @pytest.mark.asyncio
    async def test_verify_with_timeout(self, agent):
        """Test verification handles timeout gracefully"""
        agent.llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(asyncio.TimeoutError):
            await agent.verify(
                current_sql="SELECT * FROM users",
                user_query="Get all users",
                execution_result=[],
                max_retries=1,
            )

    @pytest.mark.asyncio
    async def test_standalone_function(self):
        """Test the standalone logic_verification_agent function"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "### Decision: YES\n### Reasoning: Correct"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        matches_intent, new_sql, metadata = await logic_verification_agent(
            current_sql="SELECT COUNT(*) FROM users",
            user_query="How many users are there?",
            execution_result=[{"count": 100}],
            llm_client=mock_llm,
        )

        assert matches_intent is True
        assert metadata["matches_intent"] is True


class TestLogicVerificationIntegration:
    """Integration tests for Logic Verification Agent with AutoCorrection"""

    @pytest.mark.asyncio
    async def test_empty_result_handling(self):
        """Test that empty results trigger verification failure"""
        mock_llm = Mock()
        agent = LogicVerificationAgent(mock_llm)

        # Empty result should trigger verification
        mock_response = Mock()
        mock_response.content = """
        ### Decision: NO
        ### Reasoning: Query returned no results, which is incorrect.
        ### SQL Query: SELECT * FROM demographic_race WHERE state='GA'
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        matches_intent, new_sql, metadata = await agent.verify(
            current_sql="SELECT * FROM demographic_race WHERE state='ZZ'",
            user_query="Show demographic data for Georgia",
            execution_result=[],  # Empty result
        )

        assert matches_intent is False
        assert "No results" in str(metadata.get("potential_issues", []))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
