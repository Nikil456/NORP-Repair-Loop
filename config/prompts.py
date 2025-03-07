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
