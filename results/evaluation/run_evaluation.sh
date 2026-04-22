#!/bin/bash
# Script to run SQL generation evaluation

# Default values
DATASET="./data/gold_queries.csv"
API_URL="http://localhost:8000"
LIMIT=0
OUTPUT="./evaluation_results.json"
VERBOSE=""

# Parse command line options
while getopts ":d:a:l:o:vh" opt; do
  case $opt in
    d) DATASET="$OPTARG" ;;
    a) API_URL="$OPTARG" ;;
    l) LIMIT="$OPTARG" ;;
    o) OUTPUT="$OPTARG" ;;
    v) VERBOSE="--verbose" ;;
    h) 
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  -d PATH   Path to gold dataset CSV (default: $DATASET)"
      echo "  -a URL    Base URL for the API (default: $API_URL)"
      echo "  -l NUM    Limit evaluation to first NUM queries (default: all)"
      echo "  -o PATH   Output file for results (default: $OUTPUT)"
      echo "  -v        Enable verbose output"
      echo "  -h        Show this help message"
      exit 0
      ;;
    \?) 
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :) 
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

# Show settings
echo "Evaluation Settings:"
echo "  Dataset: $DATASET"
echo "  API URL: $API_URL"
[ "$LIMIT" -gt 0 ] && echo "  Limit: $LIMIT queries" || echo "  Limit: No limit"
echo "  Output: $OUTPUT"
[ -n "$VERBOSE" ] && echo "  Verbose: Yes" || echo "  Verbose: No"

# Prepare limit argument
if [ "$LIMIT" -gt 0 ]; then
  LIMIT_ARG="--limit $LIMIT"
else
  LIMIT_ARG=""
fi

# Make sure the app is running
if ! curl -s "$API_URL" > /dev/null; then
  echo "Warning: API not responding at $API_URL"
  echo "Make sure the app is running before continuing."
  read -p "Continue anyway? (y/N) " CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborting evaluation."
    exit 1
  fi
fi

# Run the evaluation
echo "Starting evaluation..."
python3 evaluation/evaluate.py \
  --dataset "$DATASET" \
  --api-url "$API_URL" \
  --output "$OUTPUT" \
  $LIMIT_ARG \
  $VERBOSE

# Check the exit status
if [ $? -eq 0 ]; then
  echo "Evaluation completed successfully!"
  echo "Results saved to: $OUTPUT"
else
  echo "Evaluation failed with errors."
fi 