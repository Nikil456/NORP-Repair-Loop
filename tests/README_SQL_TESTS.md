# SQL Query Testing Tool

This directory contains a script for validating SQL queries against your local SQLite database. This is especially useful for verifying that a gold dataset CSV of queries works correctly with your database schema.

## About

The `test_sql_queries.py` script helps ensure that:

1. All tables in your database are accessible and contain data
2. SQL queries from a gold dataset CSV can be executed successfully on specific tables
3. All queries return non-null rows
4. Detailed error messages are reported for each failed query

## Usage

### Basic Table Testing

To test if all tables in the database are accessible and contain data:

```bash
python tests/test_sql_queries.py
```

This will:
- Connect to your local SQLite database (configured in `config/config.json`)
- Run a basic `SELECT * FROM table_name LIMIT 5` query on each table
- Report whether each query was successful and returned rows

### Testing Table-Specific Queries

To test SQL queries from a gold dataset CSV on specific tables:

```bash
python tests/test_sql_queries.py --gold-dataset path/to/your/dataset.csv
```

Optional arguments:
- `--query-column`, `-q`: Specify the column name in CSV containing SQL queries (default: "SQL Query")
- `--table-column`, `-t`: Specify the column name in CSV containing table names (default: "Table_Names")
- `--tables-only`: Only test basic table queries, skip table-specific queries
- `--fix-syntax`: Attempt to fix common SQL syntax issues for SQLite compatibility
- `--skip-missing-tables`: Skip queries that reference tables that don't exist in the database

Example with all options:

```bash
python tests/test_sql_queries.py --gold-dataset dataset/gold/gold.csv --query-column "SQL Query" --table-column "Table_Names" --fix-syntax --skip-missing-tables
```

### SQL Syntax Fixing

Many SQL queries written for MySQL or other databases may not work directly with SQLite. The `--fix-syntax` option helps address these compatibility issues by:

1. Converting MySQL-specific date functions to SQLite equivalents
2. Fixing quoting styles (backticks to double quotes)
3. Replacing `substring()` with `substr()`
4. Handling simple `concat()` expressions with the `||` operator

When this option is enabled, the script will:
- First test each query without fixes to establish a baseline
- Then apply fixes and test again
- Provide a report showing how many more queries succeeded with the fixes
- Show the exact changes made to each query

The script prioritizes showing exact errors instead of using fallback queries, so you can see exactly why a query is failing.

### Handling Missing Tables

If your gold dataset references tables that don't exist in your database, you have two options:

1. **Identify missing tables**: The script will show a report of all tables mentioned in your queries that don't exist in the database.
2. **Skip missing tables**: Use the `--skip-missing-tables` option to treat queries for non-existent tables as successful (they'll be marked as skipped).

This is useful when:
- You're testing a subset of queries that only work with certain tables
- Some tables in your gold dataset haven't been created yet
- You want to focus on testing the queries for tables that actually exist

## Table-Specific Queries Format

Your CSV file should include:
1. A column containing the SQL queries to test (default: "SQL Query")
2. A column containing the table names to run the queries on (default: "Table_Names")

Example CSV:

```csv
Natural Language Query,SQL Query,Schema,Top 5 Entries of Table,Source_Sheet,Table_Names
"How many states are in the dataset?","SELECT COUNT(DISTINCT State)",,,,"us_population"
"What is the total population?","SELECT SUM(PopulationCount)",,,,"us_population"
"Find average median income","SELECT AVG(MedianFamilyIncome)",,,,"food_access"
```

### Multiple Tables

You can specify multiple tables for a single query by providing a comma-separated list in the "Table_Names" column. The script will try the query on each table until one succeeds:

```csv
Natural Language Query,SQL Query,Schema,Top 5 Entries of Table,Source_Sheet,Table_Names
"Get housing data","SELECT COUNT(*)",,,,"housing_rent, housing_value, housing_mortgage"
```

This is useful when a query could be run on any of several tables with similar schemas.

### Dynamic Table Names

You can use the `{table}` placeholder in your queries, which will be replaced with the actual table name:

```csv
Natural Language Query,SQL Query,Schema,Top 5 Entries of Table,Source_Sheet,Table_Names
"Get top 5 states","SELECT State, SUM(PopulationCount) AS Total FROM {table} GROUP BY State ORDER BY Total DESC LIMIT 5",,,,"us_population"
```

## Error Reporting

The script provides detailed error messages for each failed query, including:

- The exact SQL error message from SQLite
- The query that was attempted (with any syntax fixes applied)
- For syntax-fixed queries, what changes were made to the original query

This helps you understand exactly why a query is failing and how to fix it.

## Notes

- All queries are executed against your local SQLite database
- The script will try each query on all specified tables until one succeeds
- The test will print results for each table attempt
- A summary of successes and failures is provided at the end
- The script verifies that tables exist before running queries on them
- Common syntax issues that cause failures include:
  - MySQL functions not supported in SQLite (`STR_TO_DATE`, `DAYOFWEEK`, etc.)
  - Quoting styles (`backticks` vs "double quotes")
  - Complex JOINs and subqueries with specific syntax requirements 