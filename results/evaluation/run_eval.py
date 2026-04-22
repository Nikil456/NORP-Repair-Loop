"""
Script that sends POST request to app and prints the responses.
This is easy to pretty print the results and testing.
"""
import requests
import json
import argparse
import pandas as pd
import random
import os
import sys

# Add the parent directory to the path to find modules
# This assumes run_eval.py is in the evaluation directory and services/config are siblings
script_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, parent_dir)

from services.service_manager import ServiceManager
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
# from util import pretty_print_results

def read_json(file_name):
    """Reads a JSON file, trying current dir then config dir."""
    try:
        try:
            with open(file_name, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            config_path = os.path.join(parent_dir, 'config', file_name) 
            with open(config_path, 'r') as file:
                return json.load(file)
    except FileNotFoundError:
        print(f"Warning: Config file '{file_name}' not found in current dir or config/. Using defaults.")
        return None
    except json.JSONDecodeError:
        print(f"Error: File '{file_name}' is not a valid JSON. Using defaults.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred reading {file_name}: {e}. Using defaults.")
        return None

def execute_sql_locally(db_tool: QuerySQLDataBaseTool, sql_query: str):
    """Executes SQL query locally using the provided DB tool."""
    if not sql_query or not isinstance(sql_query, str):
        return "Invalid SQL query for local execution"
    try:
        # Ensure the input format matches what the tool expects if necessary
        # The tool might expect a dict like {"query": sql_query}
        return db_tool.invoke({"query": sql_query})
    except Exception as e:
        error_message = f"Error executing local query: {e}"
        print(error_message)
        return error_message

def run_query(question, session_id, use_rag, use_auto_correction, generate_summary):
    url = "http://localhost:8088/query" # Updated URL
    headers = {"Content-Type": "application/json"}
    payload = {
        "session_id": session_id, 
        "question": question, 
        "message_type": "human", 
        "use_rag": use_rag,
        "use_auto_correction": use_auto_correction,
        "generate_summary": generate_summary
    }
    print("Payload:")
    print(json.dumps(payload, indent=2))
    
    response = None # Initialize response to None
    try:
        # Send POST request with a 120-second timeout
        response = requests.post(url, headers=headers, json=payload, timeout=160) 
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # Parse JSON response
        response_data = response.json()
        
        print("SQL query:")
        print(response_data.get("sql_query", "No SQL query returned"))
        print("\nQuery Results:")
        print(response_data.get("query_results", "No query result returned")[:500]) # Limit output length
        print("\nNatural Language Summary:")
        print(response_data.get("natural_language_summary", "No summary returned or generated"))
        print("\n")
        
        # Returning original_query_results assuming the backend provides it, otherwise this needs adjustment
        return (
            response_data.get("sql_query", "No SQL query returned"), 
            response_data.get("query_results", "No query result returned"), 
            # response_data.get("original_query_results", "Backend did not return original_query_results"), # Placeholder if backend doesn't return this
            response_data.get("natural_language_summary", "No summary returned or generated")
        )
        
    except requests.exceptions.Timeout:
        print(f"Request timed out after 120 seconds.")
        return ("Timeout Error", "Timeout Error", "Timeout Error") # Return specific timeout indicators
    except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if response is not None:
                print(f"Response status code: {response.status_code}")
                print(f"Response text: {response.text}")
            return ("Request Error", str(e), "Request Error", "Request Error")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response: {response.text}")
        return ("JSON Error", response.text, "JSON Error", "JSON Error")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return ("Unexpected Error", str(e), "Unexpected Error", "Unexpected Error")

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation queries against the NORP LLM backend.")
    parser.add_argument("input_csv", type=str, help="Path to the input CSV dataset (e.g., combined_dataset.csv)")
    parser.add_argument("output_csv", type=str, help="Path to save the output CSV results (e.g., evaluation_results.csv)")
    
    # Add flags for new options
    parser.add_argument("--use-rag", action='store_true', help="Enable RAG for schema retrieval.")
    parser.add_argument("--no-rag", dest='use_rag', action='store_false', help="Disable RAG.")
    parser.set_defaults(use_rag=True)

    parser.add_argument("--use-auto-correction", action='store_true', help="Enable SQL auto-correction.")
    parser.add_argument("--no-auto-correction", dest='use_auto_correction', action='store_false', help="Disable SQL auto-correction.")
    parser.set_defaults(use_auto_correction=True)

    parser.add_argument("--generate-summary", action='store_true', help="Enable natural language summary generation.")
    parser.add_argument("--no-summary", dest='generate_summary', action='store_false', help="Disable natural language summary generation.")
    parser.set_defaults(generate_summary=True)

    args = parser.parse_args()

    # --- Initialize DB Connection --- 
    config_details = read_json('config.json')
    if config_details is None:
        # Provide default config similar to app.py if config.json is missing/invalid
        config_details = {
            "db_url": "sqlite:///local_norp.db", # Adjust as needed
            "db_username": "",
            "db_password": "",
            "redis_host_url": "localhost",
            "redis_port": "6379",
            "redis_password": None,
            "nvidia_api_key": None # Or fetch from env/secure location if needed by ServiceManager
        }
        print("Using default configuration details.")

    try:
        service_manager = ServiceManager(config_details)
        db = service_manager.get_db()
        local_db_tool = QuerySQLDataBaseTool(db=db)
        print("Database connection initialized successfully.")
    except Exception as e:
        print(f"FATAL: Failed to initialize database connection: {e}")
        print("Please ensure the database is accessible and config.json is correct.")
        exit(1)
    # --- End DB Initialization ---

    start_index = 0
    output_file_exists = os.path.exists(args.output_csv)
    if output_file_exists:
        try:
            # Count existing rows to determine where to resume
            # Read only the first few rows to check for header, then count lines efficiently
            # This avoids loading the whole potentially large file into memory just for counting
            existing_df_rows = pd.read_csv(args.output_csv, nrows=1) # Read header row
            # Simple line count (more efficient for large files than pd.read_csv().shape[0])
            # with open(args.output_csv, 'r', encoding='utf-8') as f:
                # Subtract 1 for the header row
                # num_existing_results = sum(1 for line in f) - 1 
            df_to_count = pd.read_csv(args.output_csv)
            num_existing_results = df_to_count.shape[0] - 1
            
            if num_existing_results > 0:
                start_index = num_existing_results
                print(f"Output file {args.output_csv} found with {start_index} results. Resuming from input row {start_index + 1}.")
            else:
                 print(f"Output file {args.output_csv} found but is empty or only has a header. Starting from the beginning.")
                 # Overwrite if only header exists or empty
                 os.remove(args.output_csv)
                 output_file_exists = False
        except pd.errors.EmptyDataError:
             print(f"Output file {args.output_csv} exists but is empty. Starting from the beginning.")
             os.remove(args.output_csv) # Remove empty file
             output_file_exists = False
        except Exception as e:
            print(f"Error reading existing output file {args.output_csv}: {e}. Starting from the beginning.")
            # Optionally remove/backup the problematic file
            # os.remove(args.output_csv)
            output_file_exists = False
            start_index = 0

    try:
        dataset = pd.read_csv(args.input_csv, encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input CSV file not found at {args.input_csv}")
        exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        exit(1)
        
    count = 0
    syntactically_correct = []
    logically_correct = []
    execution_result = []
    llm_output = []
    original_execution_result = []
    original_query_syntactical_correctness = []
    summaries = []

    print(f"Running evaluation with flags: use_rag={args.use_rag}, use_auto_correction={args.use_auto_correction}, generate_summary={args.generate_summary}")
    print(f"Results will be saved incrementally to: {args.output_csv}")

    # Get column names from the input dataset to include in the output
    input_columns = dataset.columns.tolist()
    output_columns = input_columns + [
        'Syntactically_Correct', 'Logically_Correct', 'LLM Generated SQL Query', 
        'LLM_Query_Execution_Results', 'Correct_Query_Execution_Results', 
        'Correct_Query_Syntactical_Correctness', 'LLM_Generated_Summary'
    ]

    # Slice the dataset to start from the determined index
    dataset_to_process = dataset.iloc[start_index:]
    print(f"Processing {len(dataset_to_process)} rows from the input file (starting at index {start_index}).")

    for index, row in dataset_to_process.iterrows():
        print(f"--- Processing Original Row {index} ---") 
        count += 1 # Count how many rows are actually processed in this run
        session_id = random.randint(100000, 999999)
        question = row["Natural Language Query"]
        table_info = row['Schema'] # Note: This is sent in payload but not standard in ChatRequest
        correct_query = row['SQL Query'] # Note: This is sent in payload but not standard in ChatRequest
        
        # Data cleaning (consider moving this to a preprocessing step)
        if pd.isna(question) or pd.isna(correct_query):
            print(f"Skipping row {index} due to missing question or query.")
            # Append placeholders or handle appropriately
            syntactically_correct.append(None)
            logically_correct.append(None)
            llm_output.append("Skipped")
            execution_result.append("Skipped")
            original_execution_result.append("Skipped")
            original_query_syntactical_correctness.append(None)
            summaries.append("Skipped")
            continue

        # Clean table_info (Note: table_info is not sent to API anymore)
        if isinstance(table_info, str) and "\n" in table_info:
            table_info = table_info.replace("\n", " \n ")
        if isinstance(table_info, str):
             table_info = table_info.replace("demographic_basic", "demographics_basic") # Specific table name correction
        
        # Clean and execute correct_query locally
        cleaned_correct_query = None
        if isinstance(correct_query, str):
            cleaned_correct_query = correct_query.replace('\xa0', ' ')
            cleaned_correct_query = cleaned_correct_query.replace('%%', '%')
            cleaned_correct_query = cleaned_correct_query.replace("demographic_basic", "demographics_basic") # Specific table name correction
        
        print(f"Executing ground truth query locally: {cleaned_correct_query}")
        original_query_results = execute_sql_locally(local_db_tool, cleaned_correct_query)
        print(f"Ground truth execution result (first 500 chars): {str(original_query_results)[:500]}")

        # Run the LLM query via API
        print(f"Sending question to API: {question}")
        sql_query, query_results, summary = run_query(
            question, 
            session_id, 
            # table_info is no longer sent
            # correct_query is no longer sent
            args.use_rag, 
            args.use_auto_correction, 
            args.generate_summary
        )
        
        # Basic correctness checks (can be made more robust)
        is_syntactic = sql_query not in ["Request Error", "JSON Error", "Unexpected Error"] and "No SQL query returned" not in sql_query and (isinstance(query_results, str) and "Error" not in query_results)
        # Append to lists for final summary calculation
        syntactically_correct.append(is_syntactic) 
        print(f"Syntactical correctness: {is_syntactic}")
        llm_output.append(sql_query)
        summaries.append(summary)
        
        # Check original query results (now executed locally)
        original_correct = False
        if isinstance(original_query_results, str) and "Error" not in original_query_results and "Invalid SQL" not in original_query_results:
             original_correct = True
        elif original_query_results is not None and not isinstance(original_query_results, str): # Handles non-string results if they are valid
             original_correct = True

        if not original_correct:
             print(f"Issue with original query execution result: {original_query_results}")
             original_query_syntactical_correctness.append(False)
        else:
             # Append to list for final summary calculation
             original_query_syntactical_correctness.append(True)
        
        is_logical = False
        # Check if results are errors before attempting comparison
        llm_result_is_error = isinstance(query_results, str) and "Error" in query_results
        original_result_is_error = isinstance(original_query_results, str) and ("Error" in original_query_results or "Invalid SQL" in original_query_results)

        if is_syntactic and original_correct and not llm_result_is_error and not original_result_is_error:
            if sql_query == cleaned_correct_query: # llm query is exactly same as ground truth query
                is_logical = True
                print("Complete match (Query String)!!!")
            # Convert results to string for basic comparison. Might need refinement for complex types.
            elif str(query_results) == str(original_query_results): # llm query is different but execution results are same
                 # Caution: Comparing complex results (like lists of dicts) might require smarter comparison logic
                 is_logical = True
                 print("Complete match (Execution Results)!!!")
        # Append to list for final summary calculation
        logically_correct.append(is_logical)
        print(f"Logical correctness: {is_logical}")

        # Prepare data for the current row
        result_data = row.to_dict() # Get original data
        result_data.update({
            'Syntactically_Correct': is_syntactic,
            'Logically_Correct': is_logical,
            'LLM Generated SQL Query': sql_query,
            'LLM_Query_Execution_Results': str(query_results), # Store as string for CSV compatibility
            'Correct_Query_Execution_Results': str(original_query_results), # Store as string
            'Correct_Query_Syntactical_Correctness': original_correct,
            'LLM_Generated_Summary': summary
        })

        # Convert single row to DataFrame
        current_result_df = pd.DataFrame([result_data], columns=output_columns) # Ensure column order

        # Append to CSV
        # Write header only if file doesn't exist (first iteration after potential removal)
        write_header = not output_file_exists 
        try:
            current_result_df.to_csv(args.output_csv, mode='a', header=write_header, index=False, encoding='utf-8')
            output_file_exists = True # Set flag to true after first write
        except Exception as e:
            print(f"Error writing to CSV file {args.output_csv}: {e}")
            # Decide whether to continue or exit if writing fails
            # continue 
            exit(1)
       
    # --- Remove final dataset writing --- 
    # dataset['Syntactically_Correct'] = syntactically_correct
    # dataset['Logically_Correct'] = logically_correct
    # dataset['LLM Generated SQL Query'] = llm_output
    # dataset['LLM_Query_Execution_Results'] = execution_result # These lists are not fully populated anymore
    # dataset['Correct_Query_Execution_Results'] = original_execution_result # These lists are not fully populated anymore
    # dataset['Correct_Query_Syntactical_Correctness'] = original_query_syntactical_correctness
    # dataset['LLM_Generated_Summary'] = summaries
    
    # Calculate and print accuracy metrics (using the lists accumulated during the loop)
    # Filter out potential None values added during skipping
    valid_syntactic = [s for s in syntactically_correct if s is not None]
    valid_logical = [l for l in logically_correct if l is not None]
    valid_original_syntactic = [o for o in original_query_syntactical_correctness if o is not None]
    
    total_valid_queries = len(valid_syntactic) # Assuming all lists have same length after filtering Nones
    
    print("\n--- Evaluation Summary ---")
    print(f"Total rows processed: {count}")
    print(f"Total valid queries for metrics (this run): {total_valid_queries}")
    if total_valid_queries > 0:
        syntactic_accuracy = sum(valid_syntactic) / total_valid_queries
        logical_accuracy = sum(valid_logical) / total_valid_queries
        correct_query_validity = sum(valid_original_syntactic) / total_valid_queries
        
        print(f"Syntactically Correct LLM queries: {sum(valid_syntactic)} ({syntactic_accuracy:.2%})")
        print(f"Logically Correct LLM queries: {sum(valid_logical)} ({logical_accuracy:.2%})")
        print(f"Syntactically Correct Ground Truth queries: {sum(valid_original_syntactic)} ({correct_query_validity:.2%})")
    else:
        print("No valid queries found to calculate metrics.")
    
    # --- Remove final dataset writing --- 
    # try:
    #     dataset.to_csv(args.output_csv, index=False)
    #     print(f"\nResults saved to {args.output_csv}")
    # except Exception as e:
    #     print(f"Error saving results to CSV: {e}")
    print(f"\nEvaluation complete. Results appended to {args.output_csv}")