"""
Script that sends POST request to app and prints the responses.
This is easy to pretty print the results and testing.
"""
import requests
import json
import argparse

# Define pretty_print_results function directly in this file instead of importing it
def pretty_print_results(response_data):
    """
    Pretty print the response data from the API.
    
    Args:
        response_data: The JSON response from the API
    """
    print("\n--- RESPONSE ---")
    if "sql_query" in response_data and response_data["sql_query"]:
        print("\nSQL Query:")
        print(response_data["sql_query"])
    
    if "query_result" in response_data and response_data["query_result"]:
        print("\nQuery Result:")
        print(response_data["query_result"])
    
    if "response" in response_data:
        print("\nLLM Response:")
        print(response_data["response"])
    
    print("\n--------------\n")

def run_query(question, session_id, use_rag=True):
    url = "http://127.0.0.1:8080/query"
    headers = {"Content-Type": "application/json"}
    payload = {
        "session_id": session_id, 
        "question": question,
        "message_type": "human",
        "use_rag": use_rag
    }
    print(payload)
    
    try:
        # Send POST request
        response = requests.post(url, headers=headers, json=payload)
        # Parse JSON response
        response_data = response.json()
        
        # Use the pretty print function
        pretty_print_results(response_data)
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", help="User question", type=str)
    parser.add_argument("--session_id", help="session id", type=int)
    parser.add_argument("--use_rag", help="Use RAG for query", action="store_true", default=True)
    args = parser.parse_args()
    # question = "For each area in New York, give count of each crime type."
    # question = "Give me number of employees who are male"
    # question = "Retrieve all records from the economic_income_and_benefits table where the mean_household_income is more than 100,000 and the crime classification (Crime_Class) is 'Felony'."
    run_query(args.question, args.session_id, args.use_rag)
