# INSTRUCTIONS.md — AI Workflow Guide

This document provides everything an AI assistant (Claude, GPT, Gemini, etc.) needs to understand, build, run, and test the **NORP Repair Loop** project.

---

## Project Overview

NORP Repair Loop is a **natural language to SQL** query system with an iterative self-correction loop based on the FinStat2SQL paper. Users submit plain-English questions; the system generates MySQL SQL, executes it, verifies the logic matches the user's intent, and if errors occur it self-corrects (up to 3 attempts by default) before returning a natural-language answer.

**Core pipeline:**
```
User Query → RAG (schema retrieval) → SelfCorrectionOrchestrator
  → LLM (SQL generation) → MySQL execution 
  → LogicVerificationAgent (verify intent)
  → If error: Refine with feedback → Retry (up to 3 times)
  → NL response
```

**Key technologies:**
- **FastAPI** — REST API server on port 8000
- **LLM** — NVIDIA `meta/llama-3.3-70b-instruct` via `langchain-nvidia-ai-endpoints`
- **Database** — MySQL via SQLAlchemy + LangChain `SQLDatabase`
- **Cache** — Redis for conversation history (TTL-based, optional)
- **RAG** — Chroma vector DB with HuggingFace `sentence-transformers` embeddings
- **Self-Correction** — `services/repair_loop/SelfCorrectionOrchestrator.py`, up to 3 SQL fix attempts

---

## Repository Structure

```
NORP-Repair-Loop/
├── app/
│   └── app.py                  # FastAPI entrypoint — ALL requests start here
├── auto_correction/
│   └── auto_correction.py     # DEPRECATED — replaced by services/repair_loop/
├── config/
│   ├── config.json             # Local config (gitignored — do NOT commit)
│   └── prompts.py              # All LLM prompt templates
├── data/
│   └── vectordb/               # Chroma DB data directory
├── dataset/
│   └── norp/
│       ├── csv/                # ⚠️  NOT in repo — must obtain separately (see below)
│       └── schemas/            # 25 .txt files with CREATE TABLE statements
├── evaluation/                 # Evaluation scripts (separate from main app)
├── rag/
│   ├── rag.py                  # SchemaRAG class — vector DB retrieval
│   └── vectordb/               # Chroma persistent vector store
├── services/
│   ├── service_manager.py      # Orchestrates all services
│   ├── llm_manager/
│   │   └── LLMManager.py       # NVIDIA LLM initialization
│   ├── redis_manager/
│   │   └── RedisManager.py     # Redis conversation cache
│   ├── sql_manager/
│   │   └── DatabaseManager.py  # MySQL connection via SQLAlchemy
│   └── repair_loop/            # NEW: Self-Correction Repair Loop
│       ├── __init__.py         # Package exports
│       ├── SelfCorrectionOrchestrator.py  # Main orchestrator
│       ├── prompts.py           # FinStat2SQL-style refinement prompts
│       └── verification_agent.py # Logic verification stub
├── tests/
│   └── test_repair_loop.py    # Unit tests for repair loop
├── utils/
│   ├── setup_from_scratch.py   # Full DB + vector DB setup script
│   ├── populate_sql.py         # Load CSVs into MySQL
│   └── create_vectordb.py      # Build Chroma vector DB from schema files
├── .env                        # ⚠️  Local secrets (gitignored — NEVER commit)
├── .env.example                # Template showing all required env vars
├── requirements.txt            # Python dependencies
└── README.md                   # Quick-start guide
```

---

## Environment Variables

All secrets are loaded from a `.env` file in the project root. **Never commit `.env`.**

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `NVIDIA_API_KEY` | API key from [build.nvidia.com](https://build.nvidia.com) |
| `OPENAI_API_KEY` | OpenAI API key (used in auto-correction prompts) |
| `DB_URL` | Full SQLAlchemy URI, e.g. `mysql+mysqlconnector://root:root@localhost/norp_db` |
| `DB_USERNAME` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `REDIS_HOST_URL` | Redis hostname, e.g. `localhost` |
| `REDIS_PORT` | Redis port, e.g. `6379` |
| `REDIS_PASSWORD` | Redis password (blank string if none) |

How env vars are loaded — in `app/app.py`:
```python
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
```
Then each key is applied with `os.environ.get(...)` before passing to services.

---

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | 3.12 (tested; 3.11+ should work) |
| MySQL | Running locally, database `norp_db` must exist |
| Redis | Running on `localhost:6379` (optional — app starts without it but loses conversation memory) |
| Dataset CSVs | 25 CSV files in `dataset/norp/csv/` — **not in repo**, must obtain from course instructor |

**Install MySQL on macOS:**
```bash
brew install mysql
brew services start mysql
mysql -u root -e "CREATE DATABASE IF NOT EXISTS norp_db;"
```

**Install Redis on macOS:**
```bash
brew install redis
brew services start redis
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/Nikil456/NORP-Repair-Loop.git
cd NORP-Repair-Loop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and fill in all values
```

---

## Database & Vector DB Setup

> **Prerequisite**: You must have the 25 CSV files in `dataset/norp/csv/` before running setup.

```bash
# Full setup: populates MySQL + builds Chroma vector DB from schema files
python utils/setup_from_scratch.py
```

Or run steps individually:
```bash
# Load CSVs into MySQL only
python utils/populate_sql.py

# Build Chroma vector DB from schema .txt files only
python utils/create_vectordb.py
```

The vector DB is persisted at `rag/vectordb/` using HuggingFace embeddings (`sentence-transformers/paraphrase-MiniLM-L3-v2`). It is already built and committed to the repo for the 25 NORP schemas.

---

## Running the Server

```bash
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8000
```

The server starts at `http://127.0.0.1:8000`.

On startup, `app/app.py` initializes (at module level):
1. Loads `.env`
2. Reads `config/config.json` and overrides with env vars
3. Creates `ServiceManager` → `DatabaseManager` (MySQL), `LLMManager` (NVIDIA), `RedisManager` (Redis)
4. Creates `SchemaRAG` instance connected to `rag/vectordb/`
5. Creates `db` (`SQLDatabase`) and `llm` (ChatNVIDIA) for use in routes

---

## API Usage

### POST `/query`

Submit a natural-language question about the NORP datasets.

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "message": "What is the total population of Atlanta?", "message_type": "text", "use_rag": true, "generate_summary": false}'
```

**Request body schema:**
```json
{
  "session_id": "string — used to retrieve conversation history from Redis",
  "message": "string — the natural language question",
  "message_type": "string — type of message (e.g., 'text')",
  "use_rag": "boolean — enable RAG for schema context (default: false)",
  "generate_summary": "boolean — enable natural language summary (default: true)"
}
```

**Response body schema:**
```json
{
  "sql_query": "string — the SQL that was executed",
  "query_results": "array — raw rows from MySQL",
  "natural_language_summary": "string — human-readable summary",
  "auto_correction_used": "boolean — always true in new repair loop",
  "attempts": "number — number of attempts made (1-3)",
  "success": "boolean — whether query succeeded"
}
```

**Internal flow for each `/query` request:**
1. Retrieve conversation history from Redis (keyed by `session_id`)
2. Call `SchemaRAG` to retrieve the top-3 most relevant table schemas from the vector DB
3. Initialize `SelfCorrectionOrchestrator` with LLM, DB, Redis
4. Execute loop (up to `max_retries` times):
   a. Generate SQL using LLM (initial or refinement based on attempt)
   b. Execute SQL against MySQL via `QuerySQLDataBaseTool`
   c. If execution fails: Store error, refine with error feedback, retry
   d. If execution succeeds: Call `LogicVerificationAgent` to verify intent
   e. If logic verification fails: Store feedback, refine with logic feedback, retry
   f. If all pass: Return success
5. If `max_retries` exceeded: Return error with session history
6. Generate natural language summary if requested
7. Store updated conversation in Redis

---

## Testing the Repair Loop

### Test Case 1: Typo Fix (Orchestrator Catches Execution Error)

This test proves the orchestrator can catch SQL execution errors (typos, invalid table/column names) and retry without human intervention.

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "Show me all users",
    "message_type": "text",
    "use_rag": true,
    "generate_summary": false
  }'
```

**Expected behavior:**
- Initial SQL might have a typo (e.g., `SELECT * FROM user` instead of `users`)
- MySQL returns "Table doesn't exist" error
- Orchestrator catches error, calls refinement with error message
- Refined SQL corrects the typo
- Response shows `attempts: 2` and `success: true`

---

### Test Case 2: Logic Error (Verification Agent Catches Wrong Query)

This test proves the logic verifier catches queries that execute successfully but don't answer the user's actual question.

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-002",
    "message": "What is the total spending by each user?",
    "message_type": "text",
    "use_rag": true,
    "generate_summary": false
  }'
```

**Expected behavior:**
- Initial SQL might be `SELECT * FROM transactions` (returns raw data, not aggregated)
- Execution succeeds (no SQL error)
- Logic Verification Agent analyzes result against question
- Verification fails: "Query doesn't aggregate by user"
- Orchestrator passes feedback to refinement prompt
- Corrected SQL: `SELECT user_id, SUM(amount) FROM transactions GROUP BY user_id`
- Response shows `attempts: 2` and `success: true`

---

### Test Case 3: Happy Path (No Errors)

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-003",
    "message": "List all transaction IDs",
    "message_type": "text",
    "use_rag": true,
    "generate_summary": false
  }'
```

**Expected:** `attempts: 1`, `success: true` — no retries needed

---

## Key Files Reference

| File | Purpose |
|---|---|
| `app/app.py` | FastAPI app, config loading, `/query` route handler |
| `config/prompts.py` | All prompt templates including `SQL_SUMMARY_TEMPLATE` |
| `services/repair_loop/SelfCorrectionOrchestrator.py` | **NEW:** Main orchestrator — Generate → Execute → Verify → Refine loop |
| `services/repair_loop/prompts.py` | **NEW:** FinStat2SQL-style refinement prompts with `{logic_feedback}` |
| `services/repair_loop/verification_agent.py` | **NEW:** Logic verification stub (partner replaces with actual implementation) |
| `auto_correction/logic_verification_agent.py` | `LogicVerificationAgent` class — FinStat2SQL Logical Critic for intent verification |
| `auto_correction/auto_correction.py` | **DEPRECATED:** Replaced by `SelfCorrectionOrchestrator` |
| `rag/rag.py` | `SchemaRAG` class — Chroma vector DB retrieval |
| `services/service_manager.py` | `ServiceManager` — initializes DB, LLM, Redis |
| `services/llm_manager/LLMManager.py` | Wraps `ChatNVIDIA` with API key from env |
| `services/sql_manager/DatabaseManager.py` | `SQLDatabase.from_uri()` for MySQL |
| `services/redis_manager/RedisManager.py` | Redis client for conversation history |
| `utils/setup_from_scratch.py` | One-shot setup: MySQL tables + Chroma DB |
| `dataset/norp/schemas/` | 25 `.txt` files with `CREATE TABLE` SQL — used for RAG context |

---

## Self-Correction Orchestrator Architecture

The `SelfCorrectionOrchestrator` class implements the FinStat2SQL repair loop from the paper (Section 4.1).

### Class Definition

```python
from services.repair_loop import SelfCorrectionOrchestrator

orchestrator = SelfCorrectionOrchestrator(
    llm=llm,                    # LangChain LLM (NVIDIA/GPT/etc.)
    db=db,                      # LangChain SQLDatabase
    redis_client=redis_client,  # Redis client
    max_retries=3,              # Configurable retry limit (default: 3)
    use_rag=True,               # Enable/disable RAG schema context
    redis_ttl=3600,             # Session history TTL in seconds (default: 1 hour)
)

result = await orchestrator.execute(
    question="Your natural language question",
    session_id="unique-session-id",
)
```

### Return Value

```python
{
    "sql_query": str,           # The final SQL query executed
    "query_result": Any,        # Results from MySQL
    "success": bool,            # True if query succeeded
    "attempts": int,            # Number of attempts (1-3)
    "error": Optional[str],     # Error message if MAX_RETRIES_EXCEEDED
}
```

### Control Flow

```
1.  Initialize state: attempt = 0, current_sql = None, final_result = None
2.  Fetch schema_context via RAG (or fallback to db.get_table_info())
3.  Fetch attempt_history from Redis for session_id
4.  WHILE attempt < max_retries:
    a.  IF attempt == 0:
            sql = await _generate_sql(question, schema_context, history=None)
        ELSE:
            sql = await _refine_sql(question, failed_sql, error, schema_context, history)
    b.  result, error = await _execute_sql(sql)
    c.  IF error is not None:
            # --- Execution Error Path ---
            attempt += 1
            Store in history: {attempt, error, sql, type: "EXECUTION_ERROR"}
            CONTINUE to next iteration
    d.  ELSE:
            # --- Execution Success Path ---
            verification = await logic_verifier.verify(sql, result, question)
            e.  IF verification["matches_intent"] is True:
                    # --- Happy Path ---
                    RETURN success
                ELSE:
                    # --- Logic Error Path ---
                    feedback = f"{metadata.explanation}\n\nSuggested SQL: {corrected_sql}"
                    attempt += 1
                    Store in history: {attempt, error: feedback, sql, type: "LOGIC_ERROR"}
                    CONTINUE to next iteration
5.  # MAX_RETRIES_EXCEEDED
    RETURN failure with session_history
```

### FinStat2SQL Refinement Prompt

The orchestrator uses a structured refinement prompt (from `services/repair_loop/prompts.py`):

```
**Original User Question:** {question}
**Database Schema Context:** {schema_context}
**Previous Failed SQL Query:** ```sql {previous_sql} ```
**Database Error Returned:** {error_message}
**Logic Verification Feedback:** {logic_feedback}
**Previous Attempts History:** {attempt_history}

Instructions:
1. Think step-by-step about why the previous SQL query failed.
2. Analyze the error message and schema to identify the root cause.
3. Generate a corrected SQL query that fixes the issue.
4. Ensure the new query uses ONLY tables and columns from the provided schema.
```

---

## Running Tests

```bash
# Unit tests for repair loop
python -m pytest tests/test_repair_loop.py -v

# All unit tests
python -m pytest tests/

# Test individual components
python tests/test_llm_manager.py
python tests/test_rag.py
python tests/test_redis_conn.py
python tests/test_logic_verification_agent.py
```

### Manual API test:
```bash
python test_api.py
```

---

## Datasets

The system covers these datasets (25 MySQL tables total):

| Domain | Tables |
|---|---|
| Crime | `atlanta_crime_data`, `la_crime_data`, `nyc_crime_data`, `philly_crime_data` |
| Demographics | `demographic_race`, `demographics_basics`, `social_*` |
| Economics | `economic_commute_to_work`, `economic_health_insurance`, `economic_income_and_benefits` |
| Housing | `housing_*` (gross rent, heating fuel, mortgage, rent, value, year built) |
| Population | `us_population`, `us_population_county` |
| Other | `food_access`, `experiencing_homelessness_age_demographics`, `us_shootings` |

Full `CREATE TABLE` statements for all 25 tables are in `dataset/norp/schemas/*.txt`.

---

## Known Issues

1. **Dataset CSVs missing**: `dataset/norp/csv/` is not committed to the repo. The server starts and the API responds, but SQL queries return empty results without the data. Obtain the 25 CSVs from the course instructor and run `python utils/setup_from_scratch.py`.

2. **Redis is optional**: If Redis is not running, the app starts normally but logs `Error 61 connecting to localhost:6379`. Conversation history is not persisted across requests. Fix: `brew services start redis`.

3. **Logic Verification Agent is a stub**: The file `services/repair_loop/verification_agent.py` currently returns `{is_valid: True, feedback: None}` for testing. Replace with actual implementation from partner.

4. **OPENAI_API_KEY required**: Some prompts in the codebase still reference OpenAI. Ensure `OPENAI_API_KEY` is set in `.env` for full functionality.

---

## Configuration Reference (`config/config.json`)

This file is gitignored. Its structure (all values overridden by `.env`):

```json
{
  "openai_api_key": "",
  "nvidia_api_key": "",
  "db_url": "",
  "db_username": "",
  "db_password": "",
  "redis_host_url": "",
  "redis_port": "",
  "redis_password": ""
}
```

You do not need to edit this file if `.env` is set up correctly.

---

## Evaluation

To reproduce paper results, see [REPRODUCING_RESULTS.md](REPRODUCING_RESULTS.md).

Quick evaluation run:
```bash
bash run_evaluation.sh
```
