# SQL Chatbot with RAG for Database Queries

This application is a chatbot that interacts with users, generates SQL queries based on natural language input, and executes those queries on a database. It uses **LangChain** for conversational AI, **FastAPI** for the API, **Redis** for session management, and **Retrieval-Augmented Generation (RAG)** for enhanced query performance.

---

## Overview

### Features

- **Natural Language to SQL**: Convert plain English questions into SQL queries automatically
- **Database Integration**: Execute queries against a SQLite or MySQL database
- **Conversational Memory**: Maintain context across multiple queries using Redis
- **Schema-aware Responses**: RAG system provides relevant database schema context to improve query accuracy
- **RESTful API**: Easy integration with frontend applications

---

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- Conda (recommended) or pip
- Redis server running locally
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

### 4. Download Dataset Files

The application requires CSV data files that are not included in the repository (they're excluded in .gitignore). You need to download these files separately and place them in the correct directory:

1. Download all CSV files from the following Dropbox link:
   [NORP Dataset Files](https://www.dropbox.com/scl/fo/s38flokz0gqaw1g8hg6px/ANpD64fQsx3gqXsBCN2j2Mg?rlkey=0x1506snhcpfpfh1vq3dlfmc9&st=fpe8a1x8&dl=0)

2. Create the directory structure if it doesn't exist:
   ```bash
   mkdir -p dataset/norp/csv
   ```

3. Place all downloaded CSV files in the `dataset/norp/csv` directory.

These files contain the necessary data that will be imported into the SQLite database during the setup process.

### 5. Configuration

The application uses a configuration file at `config/config.json` with the following structure:

```json
{
  "db_url": "sqlite:///local_norp.db",
  "db_username": "",
  "db_password": "",
  "redis_host_url": "localhost",
  "redis_port": "6379",
  "redis_password": null,
  "openai_api_key": "your-openai-api-key"
}
```

Make sure this file exists and contains valid settings for your environment.

### 6. Database and RAG Setup

Run the automated setup script to:
- Create the SQLite database
- Import sample data
- Build the vector database for RAG
- Test the connections

```bash
python utils/setup_from_scratch.py
```

### 7. Starting the Server

Start the application from the project root directory:

```bash
# From the project root (not the app directory)
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8080
```

**Note**: If port 8080 is already in use, you'll see an error like `[Errno 48] Address already in use`. In that case, try a different port:

```bash
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8081
```

### 8. Testing the API

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

### Date Parsing Error

When running the application, you may encounter the following error in the logs:
```
fromisoformat: argument must be str
```

This error is related to date parsing in the application. Despite this error message, the application is still functional and can successfully retrieve and process data from the database. The error occurs when:

1. A POST request is made to the `/query` endpoint
2. The application processes the request and performs date-related operations

**Workaround**: You can safely ignore this error as it doesn't prevent the application from functioning correctly. The API will still return valid responses to your queries.

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

If you prefer to set up the RAG system manually:

1. Ensure you have the SQLite database ready:
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

### Using MySQL Instead of SQLite

To use MySQL instead of SQLite, update the database URL in `config/config.json`:

```json
"db_url": "mysql+mysqlconnector://{username}:{password}@{host}/{database_name}"
```

And make sure to provide the appropriate username and password.

## API Reference

### POST /query

Main endpoint for interacting with the chatbot.

**Request Format**:
```json
{
  "session_id": 123,
  "message": "Show me all shootings in New York",
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

---

