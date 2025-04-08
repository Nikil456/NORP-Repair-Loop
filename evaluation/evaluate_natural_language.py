#!/usr/bin/env python3
"""
Simple script to evaluate natural language query processing.
Sends questions from a dataset to the API and saves the responses.
"""

import os
import sys
import time
import json
import argparse
import pandas as pd
import requests
from tqdm import tqdm
import logging

# Add the project root to the Python path if necessary
# sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Constants
API_URL = "http://localhost:8088/query"  # Target API URL
REQUEST_TIMEOUT = 120  # Timeout for API requests in seconds
MAX_RETRIES = 3
RETRY_DELAY = 2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("evaluate_natural_language.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Evaluate natural language queries against the API")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the dataset CSV file (must contain 'Natural Language Query' column)")
    parser.add_argument("--output", type=str, default="natural_language_results.jsonl", help="Output file to save results (JSON Lines format)")
    parser.add_argument("--limit", type=int, help="Limit evaluation to first N queries")
    parser.add_argument("--api-url", type=str, default=API_URL, help="API endpoint URL")
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT, help="API request timeout in seconds")
    parser.add_argument("--start-idx", type=int, default=0, help="Start evaluation from this index")
    return parser.parse_args()

def send_query_to_api(api_url, question, session_id, timeout, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """Send a single question to the API and return the response."""
    payload = {
        "session_id": session_id,
        "question": question,
        "message_type": "question",
        "use_rag": True,
        "use_auto_correction": False
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Request timed out for question: {question[:50]}...")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Connection error for question: {question[:50]}...")
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries}: Request failed for question: {question[:50]}... Error: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            logger.error(f"All retries failed for question: {question[:50]}...")
            return None # Indicate failure after all retries
    return None # Should not be reached, but added for safety

def main():
    args = parse_args()
    
    logger.info(f"Starting evaluation...")
    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"Output File: {args.output}")
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"Using RAG: True, Auto-Correction: False")
    if args.limit:
        logger.info(f"Limiting to first {args.limit} queries")
    if args.start_idx > 0:
        logger.info(f"Starting from index {args.start_idx}")

    # Load the dataset
    try:
        df = pd.read_csv(args.dataset)
        logger.info(f"Loaded {len(df)} queries from dataset.")
    except FileNotFoundError:
        logger.error(f"Error: Dataset file not found at {args.dataset}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        sys.exit(1)

    # Check for required column
    if "Natural Language Query" not in df.columns:
        logger.error("Error: Dataset must contain a 'Natural Language Query' column.")
        sys.exit(1)

    # Apply limit and start index
    df_eval = df.iloc[args.start_idx:]
    if args.limit:
        df_eval = df_eval.head(args.limit)
    
    total_queries_to_run = len(df_eval)
    logger.info(f"Will evaluate {total_queries_to_run} queries (from index {args.start_idx}).")

    all_results = []
    start_time = time.time()

    # Open the output file in append mode if starting from a later index, otherwise write mode
    file_mode = 'a' if args.start_idx > 0 else 'w'
    
    try:
        with open(args.output, file_mode) as outfile:
            for index, row in tqdm(df_eval.iterrows(), total=total_queries_to_run, desc="Evaluating Queries"):
                question = row["Natural Language Query"]
                
                # Create a unique session ID for each query for simplicity
                session_id = f"eval_nl_{int(time.time())}_{index}"
                
                logger.info(f"Processing query #{index}: {question[:60]}...")
                
                api_response = send_query_to_api(args.api_url, question, session_id, args.timeout)
                
                if api_response:
                    # Add original question and index to the result for context
                    result_to_save = {
                        "query_index": index,
                        "original_question": question,
                        "api_response": api_response
                    }
                    # Write result as a JSON line
                    outfile.write(json.dumps(result_to_save) + '\n')
                    outfile.flush() # Ensure data is written immediately
                    logger.info(f"✓ Query #{index}: Success. Response saved.")
                else:
                    # Log failure but continue
                    logger.error(f"✗ Query #{index}: Failed to get response from API.")
                    # Optionally save a failure record
                    failure_record = {
                         "query_index": index,
                         "original_question": question,
                         "api_response": None,
                         "error": "Failed to get response after retries"
                    }
                    outfile.write(json.dumps(failure_record) + '\n')
                    outfile.flush() 

                time.sleep(0.5) # Small delay between requests to avoid overwhelming the server

    except KeyboardInterrupt:
        logger.warning("Evaluation interrupted by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during evaluation: {e}")
    finally:
        end_time = time.time()
        logger.info(f"Evaluation finished. Results saved to {args.output}")
        logger.info(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 