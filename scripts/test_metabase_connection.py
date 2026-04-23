#!/usr/bin/env python3
"""
Direct Metabase connection test for NORP Repair Loop.
Tests if the Metabase API is accessible and returns data.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.metabase_fetcher.metabase_fetcher import MetabaseFetcher

def main():
    print("=" * 60)
    print("Testing Metabase Connection")
    print("=" * 60)
    
    # Initialize fetcher
    print("\n[1] Initializing MetabaseFetcher...")
    fetcher = MetabaseFetcher()
    print("    ✓ Fetcher initialized")
    
    # Test authentication
    print("\n[2] Testing authentication...")
    try:
        session_id = fetcher.get_session_id()
        print(f"    ✓ Authenticated! Session ID: {session_id[:20]}...")
    except Exception as e:
        print(f"    ✗ Authentication failed: {e}")
        return 1
    
    # Test query from user's provided script
    print("\n[3] Testing query: SELECT COUNT(*) FROM Georgia_Crime_Data_2023")
    try:
        result, error = fetcher.execute("SELECT COUNT(*) FROM Georgia_Crime_Data_2023")
        if error:
            print(f"    ✗ Query failed: {error}")
        else:
            print(f"    ✓ Query succeeded!")
            print(f"    Result: {result}")
    except Exception as e:
        print(f"    ✗ Query error: {e}")
    
    # Test fetch_table
    print("\n[4] Testing fetch_table: Georgia_Crime_Data_2023 (limit 10)")
    try:
        df, error = fetcher.fetch_table("Georgia_Crime_Data_2023", limit=10)
        if error:
            print(f"    ✗ Fetch failed: {error}")
        else:
            print(f"    ✓ Fetch succeeded!")
            print(f"    Retrieved {len(df)} rows")
            print(f"\n    Columns: {list(df.columns)}")
            print(f"\n    First 3 rows:")
            print(df.head(3).to_string())
    except Exception as e:
        print(f"    ✗ Fetch error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())