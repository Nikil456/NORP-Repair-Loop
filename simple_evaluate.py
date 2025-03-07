#!/usr/bin/env python3
"""
Simplified evaluation script to test SQL generation with and without RAG
"""

import requests
import json
import time
import csv
import os
import argparse
import pandas as pd
import mysql.connector
from tabulate import tabulate
from tqdm import tqdm

# Configure logging directory
LOG_DIR = "eval_logs"
os.makedirs(LOG_DIR, exist_ok=True)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Simplified SQL generation evaluation")
    parser.add_argument("--dataset", type=str, default="dataset/gold/gold.csv", help="Path to gold dataset CSV")
    parser.add_argument("--api-url", type=str, default="http://localhost:8088", help="Base URL for the API")
    parser.add_argument("--output", type=str, default=f"{LOG_DIR}/results_{int(time.time())}.json", help="Output file for results (JSON)")
    parser.add_argument("--limit", type=int, help="Limit evaluation to first N queries")
    parser.add_argument("--use-rag", action="store_true", help="Enable RAG for API requests")
    parser.add_argument("--host", type=str, default="localhost", help="MySQL host")
    parser.add_argument("--user", type=str, default="root", help="MySQL username")
    parser.add_argument("--password", type=str, default="root", help="MySQL password")
    parser.add_argument("--database", type=str, default="norp_db", help="MySQL database name")
    return parser.parse_args()

def load_dataset(dataset_path, limit=None):
    """Load the evaluation dataset"""
    print(f"Loading dataset from {dataset_path}...")
    try:
        df = pd.read_csv(dataset_path)
        
        # Apply limit if specified
        if limit:
            df = df.head(limit)
            print(f"Limited to evaluating {limit} queries")
            
        print(f"Loaded {len(df)} queries for evaluation")
        return df
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None

def connect_to_mysql(host, user, password, database):
    """Connect to MySQL database"""
    print(f"Connecting to MySQL database {database} on {host}...")
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        if connection.is_connected():
            print("Connection to MySQL established successfully")
            return connection
        else:
            print("Failed to connect to MySQL")
            return None
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def execute_query(connection, query):
    """Execute a SQL query and return the results"""
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return True, results
    except Exception as e:
        return False, str(e)

def get_sql_from_api(api_url, question, use_rag=False):
    """Send a request to the API to get a SQL query for the question"""
    print(f"\nSending request to API for: '{question[:80]}...' (RAG: {use_rag})")
    
    # Create unique session ID
    session_id = f"eval_{int(time.time())}_{hash(question) % 10000}"
    
    # Prepare the API request
    url = f"{api_url}/query"
    payload = {
        "session_id": session_id,
        "question": question,
        "message_type": "question",
        "use_rag": use_rag
    }
    
    try:
        # Send the request
        print(f"  → Sending POST to {url}")
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        end_time = time.time()
        
        print(f"  → Response time: {end_time - start_time:.2f} seconds")
        print(f"  → Status code: {response.status_code}")
        
        # Check for success
        if response.status_code != 200:
            print(f"  ✗ API Error: {response.status_code}")
            return False, f"API Error: {response.status_code}", None
        
        # Extract the SQL query from the response
        response_data = response.json()
        sql_query = response_data.get("sql_query")
        
        if not sql_query:
            print(f"  ✗ No SQL query in API response")
            return False, "No SQL query in API response", None
        
        print(f"  ✓ Received SQL query: '{sql_query[:80]}...'")
        return True, "Success", sql_query
    
    except requests.exceptions.Timeout:
        print(f"  ✗ API request timed out")
        return False, "API request timed out", None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ API connection error")
        return False, "API connection error", None
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False, f"Error: {str(e)}", None

def compare_results(gold_results, generated_results):
    """Compare query results for logical equivalence"""
    # Convert to sets of tuples for comparison
    if gold_results is None and generated_results is None:
        return True
        
    if gold_results is None or generated_results is None:
        return False
        
    # Convert to DataFrames for easier comparison
    df1 = pd.DataFrame(gold_results)
    df2 = pd.DataFrame(generated_results)
    
    # Check if empty results (both should be empty)
    if df1.empty and df2.empty:
        return True
        
    # Check if dataframes have the same shape
    if df1.shape != df2.shape:
        return False
        
    # Simple set comparison of results
    gold_set = set([tuple(x) for x in gold_results])
    generated_set = set([tuple(x) for x in generated_results])
    
    return gold_set == generated_set

def evaluate_query(row, connection, api_url, use_rag=False):
    """Evaluate a single query"""
    # Extract data
    nl_query = row["Natural Language Query"]
    gold_sql = row["SQL Query"]
    
    result = {
        "nl_query": nl_query,
        "gold_sql": gold_sql,
        "use_rag": use_rag
    }
    
    # Get SQL query from API
    api_success, api_message, generated_sql = get_sql_from_api(api_url, nl_query, use_rag)
    
    result["api_success"] = api_success
    result["generated_sql"] = generated_sql
    
    if not api_success:
        result["error"] = api_message
        result["syntactically_correct"] = False
        result["logically_correct"] = False
        print(f"  ⛔ API Error: {api_message}")
        return result
    
    # Execute gold query
    print(f"  → Executing gold SQL query...")
    gold_success, gold_result = execute_query(connection, gold_sql)
    
    result["gold_execution_success"] = gold_success
    if not gold_success:
        result["gold_execution_error"] = str(gold_result)
        print(f"  ⚠ Gold SQL execution failed: {gold_result}")
    
    # Execute generated query
    print(f"  → Executing generated SQL query...")
    gen_success, gen_result = execute_query(connection, generated_sql)
    
    result["syntactically_correct"] = gen_success
    if not gen_success:
        result["execution_error"] = str(gen_result)
        result["logically_correct"] = False
        print(f"  ✗ Generated SQL execution failed: {gen_result}")
        return result
    
    # Compare results if both queries executed successfully
    if gold_success and gen_success:
        is_correct = compare_results(gold_result, gen_result)
        result["logically_correct"] = is_correct
        
        if is_correct:
            print(f"  ✓ Results match! Query is correct.")
        else:
            print(f"  ✗ Results don't match. Query is logically incorrect.")
    else:
        result["logically_correct"] = False
    
    return result

def main():
    """Main evaluation function"""
    # Parse arguments
    args = parse_args()
    
    timestamp = int(time.time())
    log_file = f"{LOG_DIR}/evaluation_{timestamp}_{'rag' if args.use_rag else 'no_rag'}.log"
    
    # Configure output logging to both file and console
    print(f"Logging to {log_file}")
    
    # Print evaluation parameters
    print("=" * 80)
    print("EVALUATION PARAMETERS:")
    print(f"  Dataset: {args.dataset}")
    print(f"  API URL: {args.api_url}")
    print(f"  Using RAG: {args.use_rag}")
    print(f"  Output file: {args.output}")
    print(f"  Log file: {log_file}")
    print("=" * 80)
    
    # Load dataset
    df = load_dataset(args.dataset, args.limit)
    if df is None:
        return
    
    # Connect to MySQL
    connection = connect_to_mysql(args.host, args.user, args.password, args.database)
    if connection is None:
        return
    
    # Initialize results
    results = []
    
    # Process each query
    print(f"\nStarting evaluation with {'RAG' if args.use_rag else 'no RAG'}...")
    start_time = time.time()
    
    try:
        # Use tqdm for progress bar
        for i, (_, row) in enumerate(tqdm(list(df.iterrows()), desc="Evaluating")):
            print(f"\n[{i+1}/{len(df)}] Evaluating: '{row['Natural Language Query'][:80]}...'")
            
            result = evaluate_query(row, connection, args.api_url, args.use_rag)
            results.append(result)
            
            # Save intermediate results every 10 queries
            if (i + 1) % 10 == 0:
                print(f"\nSaving intermediate results to {args.output}...")
                with open(args.output, 'w') as f:
                    json.dump({"results": results}, f, indent=2)
            
            # Brief pause to avoid overwhelming the API
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user!")
    except Exception as e:
        print(f"\n\nError during evaluation: {e}")
    finally:
        # Calculate metrics
        total_queries = len(results)
        api_success = sum(1 for r in results if r.get("api_success", False))
        syntactically_correct = sum(1 for r in results if r.get("syntactically_correct", False))
        logically_correct = sum(1 for r in results if r.get("logically_correct", False))
        
        # Calculate percentages
        api_success_rate = (api_success / total_queries) * 100 if total_queries > 0 else 0
        syntactical_correctness = (syntactically_correct / total_queries) * 100 if total_queries > 0 else 0
        logical_correctness = (logically_correct / total_queries) * 100 if total_queries > 0 else 0
        logical_of_syntactical = (logically_correct / syntactically_correct) * 100 if syntactically_correct > 0 else 0
        
        # Create metrics table
        metrics = {
            "API Success Rate": f"{api_success_rate:.2f}%",
            "Syntactical Correctness": f"{syntactical_correctness:.2f}%",
            "Logical Correctness": f"{logical_correctness:.2f}%",
            "Logical Correctness (of Syntactically Correct)": f"{logical_of_syntactical:.2f}%",
            "Total Queries": total_queries,
            "API Successful Queries": api_success,
            "Syntactically Correct Queries": syntactically_correct,
            "Logically Correct Queries": logically_correct
        }
        
        # Print metrics table
        print("\n" + "=" * 80)
        print("EVALUATION RESULTS:")
        print("=" * 80)
        
        metrics_table = [[k, v] for k, v in metrics.items()]
        print(tabulate(metrics_table, headers=["Metric", "Value"], tablefmt="grid"))
        
        # Save final results
        output_data = {
            "metrics": metrics,
            "results": results,
            "parameters": {
                "dataset": args.dataset,
                "api_url": args.api_url,
                "use_rag": args.use_rag,
                "limit": args.limit
            }
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nDetailed results saved to {args.output}")
        
        # Close the database connection
        if connection and connection.is_connected():
            connection.close()
            print("Database connection closed")
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        print(f"\nEvaluation complete in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main() 