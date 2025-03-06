# norp-llm
# SQL Chatbot Application

This application is a chatbot that interacts with users, generates SQL queries based on natural language input, and executes those queries on a database. It uses **LangChain** for conversational AI, **FastAPI** for the API, and **Redis** for session management.

---

## Features

- **Chatbot Interaction**: Conversational interface for users to ask SQL-related questions.
- **SQL Query Generation**: Automatically constructs SQL queries from user input.
- **Database Integration**: Executes queries against a connected database and retrieves results.
- **Session Management**: Maintains conversational context using Redis.
- **RESTful API**: Easy integration with other systems.
- **Retrieval-Augmented Generation (RAG)**: Enhances SQL query generation by providing relevant schema context.

---

## Prerequisites

### Software Requirements
- Python 3.9 or higher
- Redis server
- A running SQL database (e.g., SQLite)

## Complete Setup From Scratch

We provide a comprehensive setup script that automates the entire setup process. This script will:

1. Delete any existing SQLite database and vector database
2. Set up a new SQLite database using the configuration
3. Ingest all data into the new database
4. Set up the RAG (Retrieval-Augmented Generation) system
5. Verify Redis connectivity
6. Run all tests to make sure everything works properly

### Steps:

1. Create and activate a conda environment:

   ```bash
   conda create -n norp python=3.9
   conda activate norp
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the setup script:

   ```bash
   python utils/setup_from_scratch.py
   ```

4. The script will check dependencies, create the SQLite database, ingest all data, set up the RAG system, and run tests to verify everything is working correctly.

5. If you see "Setup completed successfully!" at the end, you're ready to use the system!

## Manual Setup

If you prefer to set up components individually, follow these instructions:

Create an environment using pip, activate the environment and install the required Python libraries using `pip`.

```bash
conda create -n NORP_llm python=3.9
conda activate NORP_LLM
pip install -r requirements.txt
```

For using an OpenAI token, create a folder named `sensitive` and a file `sensitive/openai.txt` that holds the OpenAI key.

The file `llm-engine/app/config.json` holds the details for the SQL and Redis connections. The descriptions of the fields are given below

```json
{
  "db_url": "The database URL which follows the schema mysql+mysqlconnector://{username}:{password}@{host}/{database_name}",
  "db_username": "The username of the database",
  "db_password": "The password of the database",
  "redis_host_url": "The URL of the Redis host instance",
  "redis_port": "(int) The port on which the Redis instance is being hosted",
  "redis_password": "(Optional) The password of the Redis instance if authentication is enabled"
}
```

## Setting up the Redis instance
In order to set up the Redis instance, simply connect the port number to the `llm-engine/app/RedisManager.py` and `llm-engine/app/config.json`.

## Setting up RAG for Schema Context

The RAG (Retrieval-Augmented Generation) pipeline enhances SQL query generation by providing the LLM with relevant schema context based on the user's query. This is particularly useful for databases with many tables, as it helps the model focus only on relevant tables and reduces hallucination of non-existent columns or tables.

### How RAG Works

1. Schema information from the database tables is embedded and stored in a vector database
2. When a user asks a question, the system retrieves only the most relevant tables
3. These relevant schema details are added to the prompt sent to the LLM
4. The LLM generates a more accurate SQL query with the focused context

### Setting Up RAG Manually

If you didn't use the `setup_from_scratch.py` script, you can set up RAG manually:

1. Ensure you have the SQLite database ready:
   ```bash
   # Copy the example database if you don't have one
   cp llm-engine/app/local_database_setup/local_norp.db .
   ```

2. Create the vector database:
   ```bash
   # This will process the schema files and database tables,
   # and create embeddings in the rag/vectordb directory
   python utils/create_vectordb.py
   ```

3. Test the RAG implementation:
   ```bash
   python tests/test_rag.py
   ```

4. Enable RAG in API requests by setting the `use_rag` parameter to `true`:
   ```json
   {
     "session_id": "123",
     "message": "Show me all shootings in New York",
     "message_type": "human",
     "use_rag": true
   }
   ```

## Running the app
To run the server, use the following command
```
cd ./llm-engine/app
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

## Setting up the database connection
You can use SQLite or MySQL for your database connection. Update the database URL in `config.json` accordingly.

For SQLite (default):
```json
"db_url": "sqlite:///local_norp.db"
```

For MySQL:
```json
"db_url": "mysql+mysqlconnector://{username}:{password}@{host}/{database_name}"
```

## Hitting the app with API requests
First approach is using a CURL command after the app is running.
```
Invoke-RestMethod -Uri "http://127.0.0.1:8000/query" ` 

  -Method Post ` 

  -ContentType "application/json" ` 

  -Body '{"question": "Give me the number of employees who are male", "session_id": 12345, "message_type": "human"}' 
```
Another approach is to run `test_responses.py` script.
```
python test_responses.py --question "For each month, get count of victims killed and average of victims killed in each shooting incident." --session_id 585
```

## Local Setup
1. To test locally setup local database and Redis instance in desired way and ensure to connect the port numbers and relevant URLs.
2. Now, run `create_NORP_tables.py` to create local sample tables after filling
in the correct details for the database username and password.
3. Run the app using `uvicorn app:app --reload --host 127.0.0.1 --port 8000`
4. Use `test_responses.py` script to see the results.
---

