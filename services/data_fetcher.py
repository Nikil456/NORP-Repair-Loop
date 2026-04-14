"""
Data Fetcher Interface for NORP Repair Loop.

This module defines the DataFetcher protocol that both MetabaseFetcher
and other data sources (MySQL, etc.) must implement.
"""

from typing import Tuple, Any, Optional, Protocol
import pandas as pd


class DataFetcher(Protocol):
    """
    Protocol defining the interface for data fetchers.
    
    Any class implementing this protocol can be used with the
    SelfCorrectionOrchestrator to execute queries.
    """
    
    def execute(self, query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (result, error):
            - On success: (DataFrame, None)
            - On failure: (None, error_message)
        """
        ...


class MySQLFetcher:
    """
    MySQL data fetcher using LangChain's SQLDatabase.
    
    This is a wrapper around the existing MySQL functionality
    for backward compatibility.
    """
    
    def __init__(self, db):
        """
        Initialize MySQL fetcher.
        
        Args:
            db: LangChain SQLDatabase instance
        """
        self.db = db
    
    def execute(self, query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Execute a query against MySQL.
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (DataFrame, error)
        """
        try:
            result = self.db.run(query)
            # Convert to DataFrame
            if isinstance(result, list):
                df = pd.DataFrame(result)
            else:
                df = pd.DataFrame([result])
            return df, None
        except Exception as e:
            return None, str(e)


def create_fetcher(fetcher_type: str = "metabase", **kwargs) -> DataFetcher:
    """
    Factory function to create a data fetcher.
    
    Args:
        fetcher_type: Type of fetcher ("metabase" or "mysql")
        **kwargs: Additional arguments for the fetcher
        
    Returns:
        DataFetcher instance
        
    Raises:
        ValueError: If fetcher_type is unknown
    """
    if fetcher_type == "metabase":
        from services.metabase_fetcher import MetabaseFetcher
        return MetabaseFetcher(**kwargs)
    elif fetcher_type == "mysql":
        from services.data_fetcher import MySQLFetcher
        if "db" not in kwargs:
            raise ValueError("MySQL fetcher requires 'db' parameter")
        return MySQLFetcher(db=kwargs["db"])
    else:
        raise ValueError(f"Unknown fetcher type: {fetcher_type}")


if __name__ == "__main__":
    # Test the protocol
    from services.metabase_fetcher import MetabaseFetcher
    
    # Verify MetabaseFetcher implements DataFetcher
    fetcher: DataFetcher = MetabaseFetcher()
    print(f"MetabaseFetcher implements DataFetcher: {isinstance(fetcher, DataFetcher)}")