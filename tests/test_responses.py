"""
Script that sends POST request to app and prints the responses.
This is easy to pretty print the results and testing.
"""
import requests
import json
import argparse
from util import pretty_print_results

def run_query(question, session_id):
    url = "http://127.0.0.1:8000/query"
    headers = {"Content-Type": "application/json"}
    payload = {"session_id": session_id, "question": question, "message_type": "human"}
    print(payload)
    
    try:
        # Send POST request
        response = requests.post(url, headers=headers, json=payload)
        # Parse JSON response
        response_data = response.json()
        
        print("SQL query:")
        print(response_data.get("sql_query", "No SQL query returned"))
        print("Table:")
        print(response_data.get("query_results", "No query result returned"))
    except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", help="User question", type=str)
    parser.add_argument("--session_id", help="session id", type=int)
    args = parser.parse_args()
    # question = "For each area in New York, give count of each crime type."
    # question = "Give me number of employees who are male"
    # question = "Retrieve all records from the economic_income_and_benefits table where the mean_household_income is more than 100,000 and the crime classification (Crime_Class) is 'Felony'."
    run_query(args.question, args.session_id)
