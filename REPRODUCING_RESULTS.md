// ... existing code ...

## Reproducing Results

### 1. Launch the Application

Start the FastAPI server with the following command:

```bash
# From the project root directory
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8088
```

The server will be available at `http://127.0.0.1:8088`.

### 2. Test Individual Queries

You can test individual queries using curl:

```bash
curl -X POST "http://127.0.0.1:8088/query" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 123,
    "question": "How many crimes occurred in each area?",
    "message_type": "human",
    "use_rag": true,
    "use_auto_correction": true,
    "generate_summary": true
  }'
```

Example Response:
```json
{
    "sql_query": "SELECT area_name, COUNT(*) as crime_count FROM la_crime_data GROUP BY area_name",
    "query_results": [...],
    "natural_language_summary": "This query counts the number of crimes in each area of LA",
    "correction_explanation": null,
    "correction_metadata": null,
    "auto_correction_used": true
}
```

### 3. Run Full Evaluation

To reproduce the evaluation results shown in the paper:

1. **Prepare the Gold Dataset**
   ```bash
   # Create evaluation directory if it doesn't exist
   mkdir -p evaluation/data
   
   # Download the gold dataset
   wget https://example.com/gold_dataset.csv -O evaluation/data/gold_dataset.csv
   ```

2. **Run Basic Evaluation**
   ```bash
   python evaluation/run_eval.py \
     evaluation/data/gold_dataset.csv \
     evaluation/results/basic_results.csv
   ```

3. **Run Evaluation with Different Configurations**
   ```bash
   # RAG Only
   python evaluation/run_eval.py \
     evaluation/data/gold_dataset.csv \
     evaluation/results/rag_results.csv \
     --use-rag --no-auto-correction

   # RAG + Auto-correction
   python evaluation/run_eval.py \
     evaluation/data/gold_dataset.csv \
     evaluation/results/rag_auto_results.csv \
     --use-rag --use-auto-correction
   ```

4. **Run Comprehensive Evaluation**
   ```bash
   python evaluation/evaluate.py \
     --dataset evaluation/data/gold_dataset.csv \
     --api-url "http://localhost:8088" \
     --compare-rag \
     --compare-auto-correction \
     --output evaluation/results/comprehensive_results.json
   ```

### 4. Analyze Results

The evaluation scripts produce several metrics:

1. **Syntactical Correctness:**
   - No RAG: 78.7%
   - With RAG: 84.6%
   - RAG + Auto-correction: 87.1%

2. **Execution Success Rate:**
   - Measures queries that execute without errors
   - Shows improvement with RAG and further improvement with auto-correction

3. **Result Quality:**
   - Compares results with gold standard queries
   - Evaluates both exact matches and semantic equivalence

### 5. Checkpoint and Resume

For long evaluation runs, you can use checkpointing:

```bash
python evaluation/evaluate.py \
  --dataset evaluation/data/gold_dataset.csv \
  --checkpoint evaluation/checkpoint.json \
  --compare-rag \
  --compare-auto-correction
```

If interrupted, resume from the last checkpoint:
```bash
python evaluation/evaluate.py \
  --dataset evaluation/data/gold_dataset.csv \
  --checkpoint evaluation/checkpoint.json \
  --start-idx <last_index>
```

### 6. Troubleshooting Evaluation

If you encounter issues during evaluation:

1. **API Timeouts**
   - Default timeout is 25 seconds per query
   - Adjust with `--timeout` parameter
   - Use `--max-retries` to control retry attempts

2. **Memory Issues**
   - Results are saved incrementally
   - Use `--limit` to process subset of queries
   - Monitor Redis memory usage

3. **Connection Issues**
   - Check MySQL connection settings
   - Verify API server is running
   - Check Redis connection

4. **Common Error Messages**
   - "API Error": Server not running or wrong port
   - "MySQL Error": Database connection issues
   - "Timeout Error": Increase timeout or check server load
