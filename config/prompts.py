from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

## Prompts to create SQL query
# This is the first prompt with all table schema, 3 rows of every table information
INITIAL_DATABASE_INFO_PROMPT = "You are a MySQL expert. Given an input question, create a syntactically correct MySQL query to run. Unless otherwise specified, do not return more than {top_k} rows.\n\nHere is the relevant table info: {table_info}."
# For upcoming chat, where table info is already present in the history
CONTINUATION_PROMPT = "Generate ONLY the MySQL query based on user's question and history. Filter out rows with any NULL field. If the question is unclear, try your best to create SQL query."
RESPONSE_FORMAT = " IMPORTANT: Respond ONLY with the complete SQL query, without any additional text or explanation."
# Failure message when LLM is unable to generate the SQL query
FAILURE_MESSAGE_FORMAT = " If you could not generate a SQL query, give the reason in at most 50 words."
# Aggregated Group by
GROUP_BY_PROMPT = """
    While working with MySQL databases:
    Ensure the query satisfies:
    1. All non-aggregated columns in the `SELECT` list are included in the `GROUP BY` clause or are aggregated.
    2. Use aggregate functions appropriately.
    """
GROUP_BY_PROMPT_V2 = """
1. Ensure all non-aggregated columns in the `SELECT` list are included in the `GROUP BY` clause or are aggregated.
2. Use aggregate functions appropriately to avoid grouping errors.
3. Provide meaningful aliases for calculated columns.
"""
GROUP_BY_PROMPT_V3 = """
You are a SQL expert working with MySQL databases.
Constraints:
1. Ensure all non-aggregated columns in the `SELECT` list are included in the `GROUP BY` clause or are aggregated.
2. Use aggregate functions appropriately to avoid grouping errors.
3. Provide meaningful aliases for calculated columns.
4. Use MySQL-specific syntax and functions, not SQLite syntax.
5. To list tables in a database, use the SHOW TABLES query, not sqlite_master.

For example:
Correct:
SELECT State, 
       SUM(VictimsKilled) / SUM(PopulationCount) * 1000000 AS VictimsKilledPerMillionCapita
FROM us_shootings
JOIN us_population ON us_shootings.State = us_population.State
GROUP BY State;

Incorrect:
SELECT State, 
       SUM(VictimsKilled) / PopulationCount * 1000000 AS VictimsKilledPerMillionCapita
FROM us_shootings
JOIN us_population ON us_shootings.State = us_population.State
GROUP BY State;

MySQL Examples:
1. To show all tables: SHOW TABLES;
2. To describe a table: DESCRIBE table_name;
3. To count tables: SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'norp_db';

Now, write the query for this task:
"Calculate victims killed per million capita for each state."

"""
# Chat prompt template for a new chat
INITIAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", INITIAL_DATABASE_INFO_PROMPT),
])

# Chat prompt tenplate for a continuation chat
CONTINUATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONTINUATION_PROMPT + GROUP_BY_PROMPT_V3 + RESPONSE_FORMAT + FAILURE_MESSAGE_FORMAT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

## Auto-correction prompts
# Prompt for correcting SQL queries with errors
SQL_CORRECTION_PROMPT = """You are a SQL expert tasked with correcting and improving SQL queries.
Given the following:
1. Original query: {original_query}
2. Error message: {error_message}
3. Original user request: {user_request}
4. Table Info Schema (ONLY use columns/tables that exist in the provided Table Info Schema): {table_info}

YOU CANNOT USE ANY COLUMN/TABLE THAT IS NOT PRESENT IN THE PROVIDED TABLE INFO SCHEMA FOLLNG THE KEWORD Columns:


Please provide:
1. A corrected SQL query that fixes the error
2. A brief explanation of what was wrong and how you fixed it

Remember to:
- NOT hallucinate column names, ONLY use columns that exist in the provided Table Info Schema after Columns: 
- Maintain the original intent of the query
- Sometimes the queries are complex, and might need using multiple columns and tables together.
- Fix any syntax or semantic errors
- Ensure proper table/column references
- Keep the query structure as simple as possible while achieving the goal
- Follow MySQL syntax and conventions
- Ensure GROUP BY clauses include all non-aggregated columns
- Use proper JOIN syntax and table aliases when needed
- Only use tables and columns that exist in the provided schema

IMPORTANT: Respond with a JSON object in the following format:
{{
    "corrected_query": "your corrected SQL query",
    "explanation": "your explanation of what was wrong and how you fixed it"
}}

Make sure the JSON is properly formatted and the SQL query is a single line (use spaces for formatting)."""

# Prompt for self-checking SQL queries
SQL_SELF_CHECK_PROMPT = """You are a SQL expert tasked with explaining and verifying a SQL query.
Given the following:
1. SQL Query: {sql_query}
2. Original user request: {user_request}{table_info}

Please:
1. Explain what this query does in natural language
2. Verify if it matches the user's intent
3. Identify any potential issues or improvements, particularly:
   - Check if GROUP BY includes all non-aggregated columns
   - Verify proper JOIN conditions
   - Check for proper table/column references against the provided schema
   - Ensure MySQL-specific syntax is used correctly
   - Verify that all tables and columns exist in the schema
   - Check if the query might return unexpected results

IMPORTANT: Respond with a JSON object in the following format:
{{
    "explanation": "natural language explanation of what the query does",
    "matches_intent": true/false,
    "potential_issues": ["issue 1", "issue 2"] or [] if no issues found
}}

Make sure the JSON is properly formatted and all fields are present."""

# Create ChatPromptTemplates for auto-correction
SQL_CORRECTION_TEMPLATE = ChatPromptTemplate.from_template(SQL_CORRECTION_PROMPT)
SQL_SELF_CHECK_TEMPLATE = ChatPromptTemplate.from_template(SQL_SELF_CHECK_PROMPT)

# New template for SQL Summary
SQL_SUMMARY_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "You are an expert assistant. Your task is to explain a given SQL query in plain, easy-to-understand English based on the original user question. Provide a concise summary (1-2 sentences) describing what the query does."),
    ("human", "Original Question: {user_question}\n\nSQL Query:\n```sql\n{sql_query}\n```\n\nPlease provide a plain English summary of what this SQL query is doing."),
])


# FinStat2SQL-style Refinement Prompt (for Repair Loop)
FINSTAT_REFINE_PROMPT = """You are a SQL expert performing self-correction on a failed query.

**Original User Question:** {question}

**Database Schema Context:**
{schema_context}

**Previous Failed SQL Query:**
```sql
{previous_sql}
```

**Database Error Returned:**
{error_message}

**Previous Attempts History:**
{attempt_history}

**Instructions:**
1. Think step-by-step about why the previous SQL query failed.
2. Analyze the error message and schema to identify the root cause.
3. Generate a corrected SQL query that fixes the issue.
4. Ensure the new query uses ONLY tables and columns from the provided schema.

**Output Format:**
### Reasoning: {{Step-by-step explanation}}
### Corrected SQL: ```sql
{{Your corrected SQL query}}
```
"""

# Week 10 Deliverable: Logic Verification Prompt (FinStat2SQL Self-Correction)
# This prompt acts as the Logical Critic, verifying if a successfully executed query
# matches the user's original intent, catching logical errors that syntactic checks miss.
LOGIC_VERIFICATION_PROMPT = """
<task> {user_query} </task>
<result> {sql_result} </result>

<correction>
Based on the SQL table result in <result> tag, do you think the SQL queries is correct and can fully answer the original task? 

If there is no SQL Result table on <result> tag, it means the previous queries return nothing, which is incorrect. 

If the result of SQL query is correct and the table is suitable for <task> request, you only need to return YES under *Decision* heading. You must not provide the SQL query again. 

Otherwise, return No under *Decision* heading, think step-by-step under *Reasoning* heading again and generate the correct SQL query under *SQL Query*. 

Return in the following format (### SQL Query is optional):
### Decision: {{Your decision}}
### Reasoning: {{Your reasoning}}
### SQL Query: {{Corrected SQL query}}
</correction>
"""

LOGIC_VERIFICATION_PROMPT_TEMPLATE = ChatPromptTemplate.from_template(LOGIC_VERIFICATION_PROMPT)
