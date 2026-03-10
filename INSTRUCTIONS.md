# INSTRUCTIONS.md — AI Workflow Guide

This document provides everything an AI assistant (Claude, GPT, Gemini, etc.) needs to understand, build, run, and test the **NORP Repair Loop** project.

---

## Project Overview

NORP Repair Loop is a **natural language to SQL** query system with an iterative auto-correction loop. Users submit plain-English questions; the system generates MySQL SQL, executes it, and if errors occur it self-corrects (up to 5 attempts) before returning a natural-language answer.

**Core pipeline:**
```
User Query → RAG (schema retrieval) → LLM (SQL generation) → MySQL → Auto-correction loop → NL response
```

**Key technologies:**
- **FastAPI** — REST API server on port 8088
- **LLM** — NVIDIA `meta/llama-3.3-70b-instruct` via `langchain-nvidia-ai-endpoints`
- **Database** — MySQL via SQLAlchemy + LangChain `SQLDatabase`
- **Cache** — Redis for conversation history (TTL-based, optional)
- **RAG** — Chroma vector DB with HuggingFace `sentence-transformers` embeddings
- **Auto-correction** — `auto_correction/auto_correction.py`, up to 5 SQL fix attempts

---

## Repository Structure

```
NORP-Repair-Loop/
├── app/
│   └── app.py                  # FastAPI entrypoint — ALL requests start here
├── auto_correction/
│   └── auto_correction.py      # SQL auto-correction loop (up to 5 retries)
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
│   └── sql_manager/
│       └── DatabaseManager.py  # MySQL connection via SQLAlchemy
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
python -m uvicorn app.app:app --reload --host 127.0.0.1 --port 8088
```

The server starts at `http://127.0.0.1:8088`.

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
curl -X POST http://127.0.0.1:8088/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total population of Atlanta?", "session_id": "test-session-1"}'
```

**Request body schema:**
```json
{
  "query": "string — the natural language question",
  "session_id": "string — used to retrieve conversation history from Redis"
}
```

**Response body schema:**
```json
{
  "answer": "string — natural language answer",
  "sql_query": "string — the SQL that was executed",
  "raw_results": "array — raw rows from MySQL"
}
```

**Internal flow for each `/query` request:**
1. Retrieve conversation history from Redis (keyed by `session_id`)
2. Call `SchemaRAG` to retrieve the top-3 most relevant table schemas from the vector DB
3. Build prompt using templates from `config/prompts.py` (MySQL expert persona + schema context + conversation history)
4. LLM generates SQL
5. Execute SQL against MySQL via `DatabaseManager`
6. If SQL fails, `AutoCorrection` loop retries up to 5 times with error feedback to LLM
7. Format results into a natural-language response
8. Store updated conversation in Redis

---

## Key Files Reference

| File | Purpose |
|---|---|
| `app/app.py` | FastAPI app, config loading, `/query` route handler |
| `config/prompts.py` | All prompt templates: `SQL_GENERATION_TEMPLATE`, `SQL_CORRECTION_TEMPLATE`, `SQL_SELF_CHECK_TEMPLATE`, `SUMMARY_TEMPLATE` |
| `auto_correction/auto_correction.py` | `AutoCorrection` class — iterative SQL fix loop |
| `rag/rag.py` | `SchemaRAG` class — Chroma vector DB retrieval |
| `services/service_manager.py` | `ServiceManager` — initializes DB, LLM, Redis |
| `services/llm_manager/LLMManager.py` | Wraps `ChatNVIDIA` with API key from env |
| `services/sql_manager/DatabaseManager.py` | `SQLDatabase.from_uri()` for MySQL |
| `services/redis_manager/RedisManager.py` | Redis client for conversation history |
| `utils/setup_from_scratch.py` | One-shot setup: MySQL tables + Chroma DB |
| `dataset/norp/schemas/` | 25 `.txt` files with `CREATE TABLE` SQL — used for RAG context |

---

## Running Tests

```bash
# Unit tests
python -m pytest tests/

# Test individual components
python tests/test_llm_manager.py
python tests/test_rag.py
python tests/test_redis_conn.py
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

3. **`await` bug in auto_correction.py line ~129**: `execute_query_func` is called without `await` in an async context. This is a pre-existing bug from the original repo — it causes a `RuntimeWarning` but execution continues synchronously.

4. **OpenAI vs NVIDIA**: `auto_correction/auto_correction.py` imports `ChatOpenAI` from LangChain (legacy). The main query flow uses NVIDIA LLM. Both `OPENAI_API_KEY` and `NVIDIA_API_KEY` must be set.

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
