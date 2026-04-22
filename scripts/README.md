# Scripts Directory

This directory contains various scripts for running and testing the NORP Repair Loop system.

## Evaluation Scripts (`scripts/evaluation/`)

- `evaluation_system.py` - Core evaluation framework for comparing repair loop performance
- `run_evaluation_demo.py` - Quick demo of evaluation system with mock data
- `run_comprehensive_evaluation.py` - Full evaluation against real datasets
- `run_evaluation.py` - Alternative evaluation runner

## Test Scripts

- `test_api.py` - Simple script to test the API endpoints
- `test_gold_queries.py` - Script to test SQL queries from the gold dataset against MySQL
- `test_metabase_connection.py` - Test script for Metabase API connectivity
- `test_logic_verification_metabase.py` - Test the Logic Verification Agent with Metabase data
- `test_responses.py` - (Placeholder for response testing)

## Shell Scripts

- `run_evaluation.sh` - Shell script for running evaluations
- `run_full_evaluation.sh` - Comprehensive evaluation shell script

## Usage

### Quick Demo
```bash
python scripts/evaluation/run_evaluation_demo.py
```

### Full Evaluation
```bash
python scripts/evaluation/run_comprehensive_evaluation.py
```

### Test API
```bash
python scripts/test_api.py
```

### Test Gold Queries
```bash
python scripts/test_gold_queries.py --help
```

### Shell Script Evaluation
```bash
bash scripts/run_evaluation.sh
```

## Note

The test scripts in this directory are standalone utility scripts, not pytest fixtures. They are kept separate from the `tests/` directory to distinguish them from unit tests.