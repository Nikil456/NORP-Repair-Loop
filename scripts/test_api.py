#!/usr/bin/env python3
"""
Simple script to test the API and show output.
"""

import requests
import json
import time
import sys

def test_api():
    """Test the API with a simple query"""
    print("Testing API...")
    
    # API endpoint
    url = "http://localhost:8000/query"
    
    # Sample query
    payload = {
        "session_id": int(time.time()),
        "question": "List all tables in the database",
        "message_type": "question",
        "use_rag": False
    }
    
    print(f"Sending request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send request
        response = requests.post(url, json=payload, timeout=30)
        
        # Check response
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse response
            response_data = response.json()
            
            # Print SQL query
            print("\nSQL Query:")
            print(response_data.get('sql_query', 'No SQL query found'))
            
            # Print results or error
            print("\nResults:")
            print(response_data.get('query_results', 'No results found'))
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("API Test")
    print("=" * 80)
    
    success = test_api()
    
    print("\nTest completed.")
    sys.exit(0 if success else 1) 