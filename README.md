# SQL Chatbot with RAG for Database Queries

This application is a chatbot that interacts with users, generates SQL queries based on natural language input, and executes those queries on a database. It uses **LangChain** for conversational AI, **FastAPI** for the API, **Redis** for session management, and **Retrieval-Augmented Generation (RAG)** for enhanced query performance.

> **Important**: This repository does not include database files or vector database files needed to run the application. These files are excluded via `.gitignore` and must be created by following the setup instructions below.

---

## Overview

### Features

- **Natural Language to SQL**: Convert plain English questions into SQL queries automatically
- **Database Integration**: Execute queries against a MySQL database
- **Conversational Memory**: Maintain context across multiple queries using Redis
- **Schema-aware Responses**: RAG system provides relevant database schema context to improve query accuracy
- **RESTful API**: Easy integration with frontend applications
- **Gold SQL Query Testing**: Test and validate SQL queries against the database using the gold dataset
- **Query Analysis**: Analyze success rates and failure patterns in SQL query execution

---

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- Conda (recommended) or pip
- Redis server running locally
- MySQL server (either local installation or Docker)
- Git (for cloning the repository)

### 2. Environment Setup

Create and activate a conda environment:

```bash
conda create -n norp python=3.9
conda activate norp
```

### 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Set up MySQL

The application requires a MySQL database. You have two options:

#### Option 1: Using our setup script (Recommended)

We provide a script to help you set up MySQL using Docker:

```bash
python utils/setup_mysql.py
```

This script will:
1. Check if Docker is installed
2. Help you set up a MySQL server in a Docker container
3. Create the necessary database
4. Update your configuration file automatically

#### Option 2: Manual MySQL setup

If you prefer to use an existing MySQL server:

1. Create a database named `norp_db` (or any name you prefer)
2. Update `config/config.json` with your MySQL connection details:
   ```json
   {
     "db_url": "mysql+mysqlconnector://username:password@host:port/database_name",
     "db_username": "username",
     "db_password": "password",
     ...
   }
   ```

### 5. Download Dataset Files (CRITICAL)

The application requires CSV data files that are not included in the repository (they're excluded in .gitignore). **This step is critical** as these files are needed to populate the MySQL database:

1. Download all CSV files from the following Dropbox link:
   [NORP Dataset Files](https://www.dropbox.com/scl/fo/s38flokz0gqaw1g8hg6px/ANpD64fQsx3gqXsBCN2j2Mg?rlkey=0x1506snhcpfpfh1vq3dlfmc9&st=fpe8a1x8&dl=0)

2. Create the directory structure if it doesn't exist:
   ```bash
   mkdir -p dataset/norp/csv
   ```

3. Place all downloaded CSV files in the `dataset/norp/csv` directory.

These files contain the necessary data that will be imported into the MySQL database during the setup process. Without these files, the setup script will fail and the application will not function properly.

### 6. Configuration

The application uses a configuration file at `config/config.json` with the following structure:

```json
{
  "db_url": "mysql+mysqlconnector://root:password@localhost/norp_db",
  "db_username": "root",
  "db_password": "password",
  "redis_host_url": "localhost",
  "redis_port": "6379",
  "redis_password": null,
  "openai_api_key": "your-openai-api-key"
}
```

Make sure this file exists and contains valid settings for your environment, particularly the OpenAI API key if you're using the hosted model.

### 7. Database and RAG Setup (CRITICAL)

> **Important**: This step is essential as both the MySQL database and vector database files are not included in the repository (.gitignore excludes `local_norp.db` and `rag/vectordb/*`).

Run the automated setup script to:
- Create the MySQL database tables
- Import all sample data into tables
- Build the vector database for RAG functionality
- Test the connections

```bash
python utils/setup_from_scratch.py
```

This script will:
1. Ensure your MySQL configuration is correct
2. Clean up any existing database state
3. Create the necessary tables in your MySQL database
4. Import all CSV data into the database tables
5. Process schema files and create the vector database
6. Verify Redis connectivity
7. Run tests to ensure everything works properly

Without running this script, you will not have the required database structure and the application will not function.

### 8. Starting the Server

Start the application from the project root directory:

```bash
# From the project root (not the app directory)
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8080
```

**Note**: If port 8080 is already in use, you'll see an error like `[Errno 48] Address already in use`. In that case, try a different port:

```bash
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8081
```

### 9. Testing the API

You can test the API using curl:

```bash
curl -X POST "http://127.0.0.1:8080/query" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 123, "question": "Show me all data from us_shootings", "message_type": "human", "use_rag": true}'
```

> **Important**: Note that the API expects the user query in a field named `"question"`, not `"message"`. This is different from the model definition but required for the endpoint to work correctly.

Or using the test script (which will need modification to use "question" instead of "message"):

```bash
python tests/test_responses.py --question "For each month, get count of victims killed in shooting incidents." --session_id 123
```

## Troubleshooting

### MySQL Connection Issues

If you encounter errors connecting to MySQL:

1. **Connection Refused**: Make sure your MySQL server is running
   ```bash
   # If using Docker
   docker ps | grep mysql
   # If not running, start it
   docker start norp-mysql
   ```

2. **Access Denied**: Check your username and password in config/config.json

3. **Database Not Found**: Make sure the database exists
   ```bash
   # Connect to MySQL
   mysql -u root -p
   # In MySQL console
   SHOW DATABASES;
   # If norp_db doesn't exist
   CREATE DATABASE norp_db;
   ```

4. **Run the MySQL setup script** for diagnostics:
   ```bash
   python utils/setup_mysql.py
   ```

### Missing Vector Database Files

If you encounter errors about missing vector database files:

1. Make sure you've downloaded the CSV files as described in step 5
2. Verify that you've run the setup script: `python utils/setup_from_scratch.py`
3. Check that the vector database files have been created in the `rag/vectordb/` directory

These files are generated during setup and are not included in the repository.

### Session ID Type Error

If you see an error related to the session_id validation like:
```
Input should be a valid integer, unable to parse string as an integer
```

Make sure to use an integer (not a string) for session_id in your requests:

```json
{"session_id": 123, "question": "Your question", "message_type": "human"}
```

This is a common issue when testing with curl or Python scripts. The session_id **must** be passed as a numeric value (not in quotes). For example:

**Correct:**
```json
{"session_id": 123}
```

**Incorrect:**
```json
{"session_id": "123"}
```

If you're using the test_responses.py script, ensure the session_id is passed correctly:
```bash
python tests/test_responses.py --question "Your question" --session_id 123
```

### Module Not Found Errors

If you encounter a "No module named 'services'" error, make sure you're running the application from the project root directory, not from within the app directory. The Python path needs to include the project root.

### Running on a Different Port

If the default port (8080) is already in use, you'll see an error like `[Errno 48] Address already in use`. Try a different port by modifying the port number in the command:

```bash
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8081
```

## Advanced Setup

### Manual RAG Setup

If you prefer to set up the RAG system manually (rather than using the automated setup script):

1. Ensure you have the MySQL database ready:
   ```bash
   python utils/populate_sql.py
   ```

2. Create the vector database:
   ```bash
   python utils/create_vectordb.py
   ```

3. Test the RAG implementation:
   ```bash
   python tests/test_rag.py
   ```

Both steps 1 and 2 are critical as they create the files excluded from the repository.

### Using a Remote MySQL Server

To use a remote MySQL server instead of a local installation:

1. Update the database URL in `config/config.json`:
   ```json
   "db_url": "mysql+mysqlconnector://username:password@remote-host:3306/database_name"
   ```

2. Make sure your firewall settings allow connections to the remote MySQL server.

## API Reference

### POST /query

Main endpoint for interacting with the chatbot.

**Request Format**:
```json
{
  "session_id": 123,
  "question": "Show me all shootings in New York",
  "message_type": "human",
  "use_rag": true
}
```

**Response Format**:
```json
{
  "session_id": "123",
  "response": "Here are the shootings in New York...",
  "sql_query": "SELECT * FROM us_shootings WHERE state = 'New York'",
  "sql_valid": true,
  "query_result": "[...]",
  "history": [...]
}
```

### Using the test_responses.py Script

The repository includes a test script that provides a convenient way to test the API. To use it:

1. Make sure the server is running (on port 8080)
2. Run the test script with the following format:

```bash
python tests/test_responses.py --question "Your question here" --session_id 123
```

The script will:
1. Format the request correctly, using "question" as the parameter name
2. Send the request to the API
3. Pretty-print the response, including SQL query and results

**Note**: The test script has been updated to use "question" instead of "message" in the API request to match what the server expects. If you encounter errors, make sure your test_responses.py has the correct parameter name in the payload:

```python
payload = {
    "session_id": session_id, 
    "question": question,  # Must be "question", not "message"
    "message_type": "human",
    "use_rag": use_rag
}
```

## Gold SQL Queries Testing

The repository includes tools for testing SQL queries from the gold dataset against your MySQL database:

### Running the Tests

To test gold SQL queries against your database:

```bash
python test_gold_queries.py
```

#### Command Line Arguments

The script accepts the following optional arguments:

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

### Analyzing Test Results

After running the tests, you can analyze the results using:

```bash
python analyze_query_results.py
```

This script will:
1. Provide a summary of the success/failure rate
2. Identify common error patterns
3. Show distribution of queries by table usage
4. Generate insights to help improve query generation

For more information, see `test_gold_queries_README.md`.

---

