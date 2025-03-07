# Gold SQL Queries Testing Script

This script tests the SQL queries from the gold dataset on your MySQL server to determine how many of them run successfully on the specified tables.

## Setup

1. Ensure you have the following Python packages installed:
   ```
   pip install pandas mysql-connector-python tqdm
   ```

2. Make sure your MySQL server is running and accessible with the credentials specified.

## Usage

Run the script with:

```bash
python test_gold_queries.py
```

### Command Line Arguments

The script accepts the following optional command line arguments:

- `--host`: MySQL host (default: localhost)
- `--user`: MySQL username (default: root)
- `--password`: MySQL password (default: password)
- `--database`: MySQL database name (default: norp_db)
- `--csv`: Path to the gold CSV file (default: dataset/gold/gold.csv)
- `--limit`: Limit the number of queries to test (default: None, tests all queries)

Example:
```bash
python test_gold_queries.py --host localhost --user myuser --password mypassword --database my_database --limit 100
```

## Output

The script will display:
1. A progress bar showing the testing progress
2. A summary of the results, including success rate
3. A detailed CSV file `query_test_results.csv` with:
   - Query index
   - SQL query
   - Specified tables
   - Success status
   - Error message (if any)

## How It Works

1. The script reads the gold CSV file, which should contain SQL queries and their associated table names
2. For each query, it:
   - Extracts the specified table names from the "Table_Names" column
   - Verifies that the tables mentioned in the query exist in the database
   - Attempts to execute the query
   - Records whether the execution was successful
3. Finally, it calculates statistics on how many queries ran successfully

## Troubleshooting

- If you encounter connection issues, verify your MySQL credentials and ensure the server is running
- If specific queries fail, check the error messages in the results CSV file
- For queries with complex table references, you may need to modify the table name extraction logic 