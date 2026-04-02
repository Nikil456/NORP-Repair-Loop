import requests
import pandas as pd
import os
from typing import Optional, Tuple, Any
from dotenv import load_dotenv

load_dotenv()


class MetabaseFetcher:
    """
    Fetches data from Metabase API for NORP datasets.
    
    Provides methods to authenticate and execute native SQL queries
    against the Metabase-backed NORP database.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize the Metabase fetcher.
        
        Args:
            base_url: Metabase API base URL (default from env)
            username: Metabase username (default from env)
            password: Metabase password (default from env)
        """
        self.base_url = base_url or os.environ.get(
            'METABASE_BASE_URL', 
            'http://130.207.3.31/norpmetabase/api'
        )
        self.username = username or os.environ.get('METABASE_USERNAME')
        self.password = password or os.environ.get('METABASE_PASSWORD')
        self._session_id: Optional[str] = None
    
    @property
    def session_id(self) -> str:
        """Get cached session ID, or authenticate if not cached."""
        if self._session_id is None:
            self._session_id = self.get_session_id()
        return self._session_id
    
    def get_session_id(self) -> str:
        """
        Authenticate with Metabase and get session ID.
        
        Returns:
            Session ID string
            
        Raises:
            requests.HTTPError: If authentication fails
        """
        response = requests.post(
            f"{self.base_url}/session",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        response.raise_for_status()
        self._session_id = response.json()["id"]
        return self._session_id
    
    def execute(
        self, 
        query: str, 
        database: int = 2
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Execute a native SQL query against the Metabase API.
        
        Args:
            query: SQL query string
            database: Database ID (default: 2 for NORP)
            
        Returns:
            Tuple of (DataFrame or None, error message or None)
            - On success: (DataFrame, None)
            - On failure: (None, error_message)
        """
        try:
            if self._session_id is None:
                self.get_session_id()
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Metabase-Session": self._session_id,
            }
            
            payload = {
                "database": database,
                "type": "native",
                "native": {
                    "query": query,
                    "template-tags": {},
                },
                "parameters": [],
            }
            
            response = requests.post(
                f"{self.base_url}/dataset",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            
            df = self._parse_response(response.json())
            return df, None
            
        except Exception as e:
            return None, str(e)
    
    def fetch_table(
        self,
        table_name: str,
        limit: int = 100,
        database: int = 2,
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Fetch all rows from a specific table.
        
        Args:
            table_name: Name of the table (e.g., 'Georgia_Crime_Data_2023')
            limit: Maximum number of rows to fetch
            database: Database ID
            
        Returns:
            Tuple of (DataFrame, error)
        """
        # Sanitize table name to prevent SQL injection
        safe_table_name = table_name.replace(";", "").replace("--", "")
        query = f"SELECT * FROM {safe_table_name} LIMIT {limit}"
        return self.execute(query, database)
    
    def _parse_response(self, response_data: dict) -> pd.DataFrame:
        """
        Parse Metabase response into Pandas DataFrame.
        
        Args:
            response_data: JSON response from Metabase API
            
        Returns:
            Pandas DataFrame with query results
            
        Raises:
            ValueError: If response format is unexpected
        """
        if 'data' not in response_data:
            raise ValueError(f"Unexpected response format: {response_data}")
        
        data = response_data['data']
        
        # Extract rows and columns
        rows = data.get('rows', [])
        cols = data.get('cols', [])
        
        # Get column names from cols
        if cols:
            column_names = [col.get('name', f'col_{i}') for i, col in enumerate(cols)]
        else:
            column_names = None
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=column_names)
        return df
    
    def close(self) -> None:
        """Clear the cached session ID."""
        self._session_id = None


# Convenience function for direct usage
def fetch_from_metabase(
    query: str,
    database: int = 2,
    **kwargs
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Convenience function to fetch data from Metabase.
    
    Args:
        query: SQL query string
        database: Database ID (default: 2)
        **kwargs: Additional arguments passed to MetabaseFetcher
        
    Returns:
        Tuple of (DataFrame, error)
    """
    fetcher = MetabaseFetcher(**kwargs)
    return fetcher.execute(query, database)


if __name__ == "__main__":
    # Test the fetcher
    fetcher = MetabaseFetcher()
    
    # Test query as specified
    print("Testing: SELECT * FROM Georgia_Crime_Data_2023 LIMIT 100")
    df, error = fetcher.fetch_table("Georgia_Crime_Data_2023", limit=100)
    
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Retrieved {len(df)} rows")
        print(df.head())