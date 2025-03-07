#!/bin/bash
# Script to run evaluation with and without RAG

# Define conda environment and paths
CONDA_ENV="norp"
DATASET="dataset/gold/gold.csv"
API_URL="http://localhost:8000"
OUTPUT_DIR="evaluation_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$OUTPUT_DIR/logs"

# Create output directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Define output file paths
OUTPUT_NO_RAG="$OUTPUT_DIR/no_rag_results_$TIMESTAMP.json"
OUTPUT_RAG="$OUTPUT_DIR/rag_results_$TIMESTAMP.json"
LOG_NO_RAG="$LOG_DIR/no_rag_$TIMESTAMP.log"
LOG_RAG="$LOG_DIR/rag_$TIMESTAMP.log"
COMPARISON_CSV="$OUTPUT_DIR/comparison_$TIMESTAMP.csv"
COMPARISON_LOG="$LOG_DIR/comparison_$TIMESTAMP.log"

# Function to check if server is running
check_server() {
  if curl -s "$API_URL" > /dev/null; then
    echo "Server is running"
    return 0
  else
    echo "Server is not running"
    return 1
  fi
}

# Kill any process using port 8000
kill_server() {
  echo "Checking for processes using port 8000..."
  PID=$(lsof -ti:8000)
  if [ ! -z "$PID" ]; then
    echo "Killing process $PID using port 8000"
    kill -9 $PID
    sleep 2
  else
    echo "No process found using port 8000"
  fi
}

# Start the server
start_server() {
  echo "Starting app server with uvicorn..."
  # Use nohup to keep the server running even if the terminal is closed
  cd "$(dirname "$0")"  # Change to script directory to ensure proper Python path
  nohup conda run -n $CONDA_ENV python -m uvicorn app.app:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/server_$TIMESTAMP.log" 2>&1 &
  SERVER_PID=$!
  echo "Server started with PID: $SERVER_PID"
  
  # Wait for server to start (max 30 seconds)
  for i in {1..30}; do
    if check_server; then
      echo "Server started successfully after $i seconds"
      return 0
    fi
    echo "Waiting for server to start ($i/30)..."
    sleep 1
  done
  
  echo "Failed to start server within 30 seconds"
  return 1
}

# Run evaluation
run_evaluation() {
  local use_rag=$1
  local output_file=$2
  local log_file=$3
  
  echo "Running evaluation $([ "$use_rag" = true ] && echo "with" || echo "without") RAG..."
  
  # Build the command with correct MySQL credentials
  cmd="python evaluation/evaluate.py --dataset $DATASET --api-url $API_URL --output $output_file --user root --password root --verbose"
  
  # Add RAG flag if needed
  if [ "$use_rag" = true ]; then
    cmd="$cmd --use-rag"
  fi
  
  # Run the evaluation using the conda environment and show output in real-time
  echo "Executing: $cmd"
  conda run -n $CONDA_ENV $cmd 2>&1 | tee "$log_file"
  
  # Check if output file was created
  if [ -f "$output_file" ]; then
    echo "Evaluation completed successfully. Results saved to $output_file"
    echo "Logs saved to $log_file"
    return 0
  else
    echo "Evaluation failed. No output file created."
    echo "See log file for details: $log_file"
    return 1
  fi
}

# Compare results
compare_results() {
  local no_rag_file=$1
  local rag_file=$2
  local output_csv=$3
  local log_file=$4
  
  echo "Comparing evaluation results..."
  
  # Check if both files exist
  if [ ! -f "$no_rag_file" ] || [ ! -f "$rag_file" ]; then
    echo "Error: One or both result files missing. Cannot compare."
    return 1
  fi
  
  # Run comparison
  conda run -n $CONDA_ENV python compare_evaluation_results.py --no-rag "$no_rag_file" --rag "$rag_file" --output "$output_csv" | tee "$log_file"
  
  if [ -f "$output_csv" ]; then
    echo "Comparison completed. Results saved to $output_csv"
    echo "Comparison log saved to $log_file"
    return 0
  else
    echo "Comparison failed. No output CSV created."
    return 1
  fi
}

# Main script execution
echo "=== Starting Evaluation Process ==="
echo "Timestamp: $TIMESTAMP"
echo "Conda Environment: $CONDA_ENV"
echo "Dataset: $DATASET"
echo "API URL: $API_URL"

# Make sure no server is running on port 8000
kill_server

# Start the server
start_server
if [ $? -ne 0 ]; then
  echo "Failed to start server. Exiting."
  exit 1
fi

# Run evaluation without RAG
run_evaluation false "$OUTPUT_NO_RAG" "$LOG_NO_RAG"
NO_RAG_SUCCESS=$?

# Run evaluation with RAG
run_evaluation true "$OUTPUT_RAG" "$LOG_RAG"
RAG_SUCCESS=$?

# Kill the server
echo "Shutting down the server..."
kill_server

# Compare results if both evaluations were successful
if [ $NO_RAG_SUCCESS -eq 0 ] && [ $RAG_SUCCESS -eq 0 ]; then
  compare_results "$OUTPUT_NO_RAG" "$OUTPUT_RAG" "$COMPARISON_CSV" "$COMPARISON_LOG"
else
  echo "Skipping comparison as one or both evaluations failed"
fi

# Final output
echo ""
echo "=== Evaluation Process Complete ==="
echo "Timestamp: $TIMESTAMP"
echo "Results without RAG: $OUTPUT_NO_RAG (Success: $([ $NO_RAG_SUCCESS -eq 0 ] && echo "Yes" || echo "No"))"
echo "Results with RAG: $OUTPUT_RAG (Success: $([ $RAG_SUCCESS -eq 0 ] && echo "Yes" || echo "No"))"
echo "Logs without RAG: $LOG_NO_RAG"
echo "Logs with RAG: $LOG_RAG"
echo "Comparison CSV: $COMPARISON_CSV"
echo "Comparison Log: $COMPARISON_LOG"
echo "" 