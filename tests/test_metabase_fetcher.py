import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.metabase_fetcher import MetabaseFetcher


class TestMetabaseFetcherInit:
    """Test MetabaseFetcher initialization."""
    
    def test_default_initialization(self):
        """Test initialization with defaults."""
        fetcher = MetabaseFetcher()
        assert fetcher.base_url == "http://130.207.3.31/norpmetabase/api"
        assert fetcher._session_id is None
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        fetcher = MetabaseFetcher(
            base_url="http://custom.api.com",
            username="testuser",
            password="testpass"
        )
        assert fetcher.base_url == "http://custom.api.com"
        assert fetcher.username == "testuser"
        assert fetcher.password == "testpass"
        assert fetcher._session_id is None


class TestMetabaseFetcherSession:
    """Test session ID management."""
    
    @patch('services.metabase_fetcher.metabase_fetcher.requests.post')
    def test_get_session_id(self, mock_post):
        """Test session ID retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "test-session-123"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        fetcher = MetabaseFetcher(username="test", password="test")
        session_id = fetcher.get_session_id()
        
        assert session_id == "test-session-123"
        assert fetcher._session_id == "test-session-123"
        mock_post.assert_called_once()
    
    @patch('services.metabase_fetcher.metabase_fetcher.requests.post')
    def test_session_cached(self, mock_post):
        """Test session ID is cached after first call."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "cached-session"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        fetcher = MetabaseFetcher(username="test", password="test")
        
        # First call
        _ = fetcher.session_id
        # Second call should use cached
        _ = fetcher.session_id
        
        # Only one POST call should be made
        assert mock_post.call_count == 1


class TestMetabaseFetcherExecute:
    """Test query execution."""
    
    @patch('services.metabase_fetcher.metabase_fetcher.requests.post')
    def test_execute_success(self, mock_post):
        """Test successful query execution."""
        # Mock session response
        session_response = Mock()
        session_response.json.return_value = {"id": "session-123"}
        session_response.raise_for_status = Mock()
        
        # Mock query response
        query_response = Mock()
        query_response.json.return_value = {
            "data": {
                "rows": [["1", "John", "Georgia"], ["2", "Jane", "Georgia"]],
                "cols": [
                    {"name": "id"},
                    {"name": "name"},
                    {"name": "state"}
                ]
            }
        }
        query_response.raise_for_status = Mock()
        
        # Return different responses for different calls
        mock_post.side_effect = [session_response, query_response]
        
        fetcher = MetabaseFetcher(username="test", password="test")
        result, error = fetcher.execute("SELECT * FROM users")
        
        assert error is None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["id", "name", "state"]
    
    @patch('services.metabase_fetcher.metabase_fetcher.requests.post')
    def test_execute_failure(self, mock_post):
        """Test query execution failure."""
        # Mock session response
        session_response = Mock()
        session_response.json.return_value = {"id": "session-123"}
        session_response.raise_for_status = Mock()
        
        # Mock error response
        query_response = Mock()
        query_response.raise_for_status = Mock(side_effect=Exception("Query failed"))
        mock_post.side_effect = [session_response, query_response]
        
        fetcher = MetabaseFetcher(username="test", password="test")
        result, error = fetcher.execute("SELECT * FROM invalid")
        
        assert result is None
        assert "Query failed" in error


class TestMetabaseFetcherFetchTable:
    """Test table fetching."""
    
    @patch('services.metabase_fetcher.metabase_fetcher.requests.post')
    def test_fetch_table(self, mock_post):
        """Test fetching a table."""
        # Mock session response
        session_response = Mock()
        session_response.json.return_value = {"id": "session-123"}
        session_response.raise_for_status = Mock()
        
        # Mock query response
        query_response = Mock()
        query_response.json.return_value = {
            "data": {
                "rows": [["1", "Crime"], ["2", "Crime"]],
                "cols": [
                    {"name": "id"},
                    {"name": "category"}
                ]
            }
        }
        query_response.raise_for_status = Mock()
        
        mock_post.side_effect = [session_response, query_response]
        
        fetcher = MetabaseFetcher(username="test", password="test")
        result, error = fetcher.fetch_table("Georgia_Crime_Data_2023", limit=10)
        
        assert error is None
        assert isinstance(result, pd.DataFrame)
        # Verify LIMIT is in the query
        call_args = mock_post.call_args_list[1]
        assert "LIMIT 10" in str(call_args)


class TestMetabaseFetcherParseResponse:
    """Test response parsing."""
    
    def test_parse_response_with_columns(self):
        """Test parsing response with column names."""
        fetcher = MetabaseFetcher()
        
        response_data = {
            "data": {
                "rows": [[1, "John"], [2, "Jane"]],
                "cols": [
                    {"name": "id"},
                    {"name": "name"}
                ]
            }
        }
        
        df = fetcher._parse_response(response_data)
        
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["id", "name"]
        assert len(df) == 2
    
    def test_parse_response_without_columns(self):
        """Test parsing response without column names."""
        fetcher = MetabaseFetcher()
        
        response_data = {
            "data": {
                "rows": [[1, "John"], [2, "Jane"]],
                "cols": []
            }
        }
        
        df = fetcher._parse_response(response_data)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
    
    def test_parse_response_error(self):
        """Test parsing invalid response."""
        fetcher = MetabaseFetcher()
        
        response_data = {"error": "Something went wrong"}
        
        with pytest.raises(ValueError):
            fetcher._parse_response(response_data)


class TestMetabaseFetcherClose:
    """Test close method."""
    
    def test_close_clears_session(self):
        """Test that close clears the session ID."""
        fetcher = MetabaseFetcher()
        fetcher._session_id = "test-session"
        
        fetcher.close()
        
        assert fetcher._session_id is None


class TestFetchFromMetabase:
    """Test convenience function."""
    
    @patch('services.metabase_fetcher.metabase_fetcher.MetabaseFetcher')
    def test_convenience_function(self, mock_fetcher_class):
        """Test fetch_from_metabase convenience function."""
        from services.metabase_fetcher import fetch_from_metabase
        
        mock_fetcher = Mock()
        mock_fetcher.execute.return_value = (pd.DataFrame(), None)
        mock_fetcher_class.return_value = mock_fetcher
        
        result, error = fetch_from_metabase("SELECT * FROM test")
        
        mock_fetcher_class.assert_called_once()
        mock_fetcher.execute.assert_called_once_with("SELECT * FROM test", 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])