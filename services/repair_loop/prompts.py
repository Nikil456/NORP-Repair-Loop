from langchain_core.prompts import ChatPromptTemplate

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

**Logic Verification Feedback:**
{logic_feedback}

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

FINSTAT_INITIAL_PROMPT = """You are a MySQL expert. Given an input question, create a syntactically correct MySQL query to run.

**Database Schema:**
{schema_context}

**User Question:** {question}

**Instructions:**
1. Generate a SQL query that answers the user's question.
2. Use only tables and columns from the provided schema.
3. Filter out rows with NULL fields where appropriate.
4. Respond with ONLY the SQL query, no explanation.

**Output Format:**
```sql
{{Your SQL query}}
```
"""

FINSTAT_REFINE_TEMPLATE = ChatPromptTemplate.from_template(FINSTAT_REFINE_PROMPT)
FINSTAT_INITIAL_TEMPLATE = ChatPromptTemplate.from_template(FINSTAT_INITIAL_PROMPT)
