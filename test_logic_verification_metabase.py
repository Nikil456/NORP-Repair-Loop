#!/usr/bin/env python3
"""
Simple test script to verify Logic Verification Agent works with Metabase data
"""

import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.metabase_fetcher.metabase_fetcher import MetabaseFetcher
from auto_correction.logic_verification_agent import logic_verification_agent
from services.llm_manager.LLMManager import LLMManager

async def test_logic_verification():
    """Test the Logic Verification Agent with Metabase data"""

    print("🔍 Testing Logic Verification Agent with Metabase Data")
    print("=" * 60)

    # Initialize LLM
    print("1. Initializing LLM...")
    llm_manager = LLMManager()
    llm = llm_manager.llm
    print("   ✓ LLM initialized")

    # Initialize MetabaseFetcher
    print("\n2. Initializing MetabaseFetcher...")
    fetcher = MetabaseFetcher()
    print("   ✓ MetabaseFetcher initialized")

    # Test basic query execution
    print("\n3. Testing basic query execution...")
    test_query = "SELECT COUNT(*) FROM Georgia_Crime_Data_2023"
    try:
        result_tuple = fetcher.execute(test_query)
        if result_tuple[1]:  # error message
            print(f"   ❌ Query failed: {result_tuple[1]}")
            return
        result = result_tuple[0]  # DataFrame
        print(f"   ✓ Query executed successfully: {result.iloc[0, 0]} records")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return

    # Initialize Logic Verification Agent
    print("\n3. Initializing Logic Verification Agent...")
    # We'll use the standalone function instead of the class
    print("   ✓ Logic Verification Agent ready")

    # Test logic verification with a simple case
    print("\n4. Testing logic verification...")

    # Create a test case: query that should work
    question = "How many crime records are there?"
    sql_query = "SELECT COUNT(*) FROM Georgia_Crime_Data_2023"

    print(f"   Question: {question}")
    print(f"   SQL Query: {sql_query}")

    try:
        # Execute the query first
        result_tuple = fetcher.execute(sql_query)
        if result_tuple[1]:  # error message
            print(f"   ❌ Query execution failed: {result_tuple[1]}")
            return
        
        result = result_tuple[0]  # DataFrame
        result_str = str(result.iloc[0, 0]) if not result.empty else "No results"

        print(f"   Query Result: {result_str}")

        # Now test logic verification using the standalone function
        matches_intent, correction, metadata = await logic_verification_agent(
            current_sql=sql_query,
            user_query=question,
            execution_result=result_str,
            llm_client=llm
        )

        print("   Logic Verification Result:")
        print(f"     - Matches Intent: {matches_intent}")
        if correction:
            print(f"     - Correction: {correction}")
        if metadata:
            print(f"     - Metadata: {metadata}")

        if matches_intent:
            print("   ✅ Logic verification passed!")
        else:
            print("   ⚠️  Logic verification flagged an issue")

    except Exception as e:
        print(f"   ❌ Logic verification failed: {e}")
        return

    print("\n" + "=" * 60)
    print("🎉 Test completed successfully!")
    print("The Logic Verification Agent is working with Metabase data!")

if __name__ == "__main__":
    asyncio.run(test_logic_verification())