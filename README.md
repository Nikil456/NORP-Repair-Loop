# NORP Repair Loop

## Prerequisites

- Python 3.11+
- MySQL running locally
- Redis running locally
- NVIDIA and OpenAI API keys

## Setup

**1. Clone the repo and install dependencies**

```bash
git clone https://github.com/Nikil456/NORP-Repair-Loop.git
python -m pip install -r requirements.txt
```

**2. Configure environment variables**

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
DB_URL=mysql+mysqlconnector://root:your_password@localhost/norp_db
DB_USERNAME=your_db_username
DB_PASSWORD=your_db_password
REDIS_HOST_URL=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
OPENAI_API_KEY=your_openai_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

**3. Start MySQL and Redis**

```bash
brew services start mysql
brew services start redis
```

**4. Set up the database**

Place CSV data files in `dataset/norp/csv/`, then run:

```bash
python utils/setup_from_scratch.py
```

**5. Start the server**

```bash
python app/app.py
```

The server will be available at `http://127.0.0.1:8000`

## Sending a Query

In a second terminal while the server is running, send queries using curl:

```bash
curl -X POST "http://127.0.0.1:8000/query" \
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

Example response:

```json
{
    "sql_query": "SELECT area_name, COUNT(*) as crime_count FROM la_crime_data GROUP BY area_name",
    "query_results": "...",
    "natural_language_summary": "This query counts the number of crimes in each area.",
    "auto_correction_used": true,
    "attempts": 1,
    "success": true
}
```

**Note**: The repair loop will attempt up to 3 times to generate valid SQL. If all attempts fail, you'll see `"success": false` and `"error": "MAX_RETRIES_EXCEEDED"`. This happens when API keys are not configured.

**Important**: Make sure your `NVIDIA_API_KEY` and `OPENAI_API_KEY` environment variables are set for the repair loop to generate actual SQL queries.

