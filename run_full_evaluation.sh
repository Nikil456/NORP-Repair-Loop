#!/bin/bash
# Script to run evaluation with and without RAG

# Define variables
DATASET="dataset/gold/gold.csv"
API_URL="http://localhost:8000"
OUTPUT_DIR="evaluation_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE_NO_RAG="$OUTPUT_DIR/no_rag_evaluation_$TIMESTAMP.log"
LOG_FILE_WITH_RAG="$OUTPUT_DIR/with_rag_evaluation_$TIMESTAMP.log"
OUTPUT_FILE_NO_RAG="$OUTPUT_DIR/no_rag_evaluation_$TIMESTAMP.json"
OUTPUT_FILE_WITH_RAG="$OUTPUT_DIR/with_rag_evaluation_$TIMESTAMP.json"
COMPARISON_CSV="$OUTPUT_DIR/comparison_$TIMESTAMP.csv"
COMPARISON_LOG="$OUTPUT_DIR/comparison_$TIMESTAMP.log"
CONDA_ENV="norp"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Start the app server in background
echo "Starting the app server..."
conda run -n $CONDA_ENV python app/app.py &
APP_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 10

# Check if server is running
if ! curl -s "$API_URL" > /dev/null; then
    echo "Error: Server did not start properly"
    kill $APP_PID
    exit 1
fi

echo "Server started successfully"

# Run evaluation without RAG
echo "Running evaluation without RAG..."
conda run -n $CONDA_ENV python evaluation/evaluate.py --dataset "$DATASET" --api-url "$API_URL" --output "$OUTPUT_FILE_NO_RAG" --verbose > "$LOG_FILE_NO_RAG" 2>&1
echo "No RAG evaluation completed. Results saved to $OUTPUT_FILE_NO_RAG, logs saved to $LOG_FILE_NO_RAG"

# Run evaluation with RAG
echo "Running evaluation with RAG..."
conda run -n $CONDA_ENV python evaluation/evaluate.py --dataset "$DATASET" --api-url "$API_URL" --output "$OUTPUT_FILE_WITH_RAG" --use-rag --verbose > "$LOG_FILE_WITH_RAG" 2>&1
echo "With RAG evaluation completed. Results saved to $OUTPUT_FILE_WITH_RAG, logs saved to $LOG_FILE_WITH_RAG"

# Shutdown the server
echo "Shutting down the server..."
kill $APP_PID

# Run comparison
echo "Comparing evaluation results..."
conda run -n $CONDA_ENV python ./compare_evaluation_results.py --no-rag "$OUTPUT_FILE_NO_RAG" --rag "$OUTPUT_FILE_WITH_RAG" --output "$COMPARISON_CSV" | tee "$COMPARISON_LOG"

# Final output
echo "Evaluation complete!"
echo "Results without RAG: $OUTPUT_FILE_NO_RAG"
echo "Results with RAG: $OUTPUT_FILE_WITH_RAG"
echo "Logs without RAG: $LOG_FILE_NO_RAG"
echo "Logs with RAG: $LOG_FILE_WITH_RAG"
echo "Comparison CSV: $COMPARISON_CSV"
echo "Comparison Log: $COMPARISON_LOG" 