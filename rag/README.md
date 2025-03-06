# Schema RAG for SQL Generation

This module implements Retrieval-Augmented Generation (RAG) to enhance SQL query generation by providing relevant schema context to the LLM.

## Overview

The RAG system addresses a critical challenge in SQL generation: providing the model with just the relevant tables and schema information, rather than overwhelming it with the entire database schema. This becomes especially important in databases with hundreds of tables and relationships.

## How It Works

1. **Schema Vectorization**: For each table in the database, we create a textual document with:
   - Table name
   - Column names and types
   - Relationships to other tables
   - A natural language description of the table's purpose

2. **Vector Storage**: These textual documents are embedded using a language model (Sentence Transformers) and stored in a Chroma vector database.

3. **Retrieval**: When a user submits a query, we:
   - Embed the query using the same model
   - Perform a similarity search to find the most relevant table schemas
   - Return only the top k most relevant schema documents

4. **Prompt Augmentation**: The relevant schema information is added to the prompt sent to the LLM, providing focused context for SQL generation.

## Setup

### Option 1: Complete Setup (Recommended)

The easiest way to set up the entire system, including the RAG component, is to use our comprehensive setup script:

```bash
# Make sure you're in the correct conda environment
conda activate norp

# Run the setup script
python utils/setup_from_scratch.py
```

This script will:
- Clean any existing databases
- Set up a new SQLite database
- Ingest all data
- Create the vector database for RAG
- Run tests to verify everything works correctly

### Option 2: Manual RAG Setup

If you already have the database set up and only want to create the vector database:

```bash
python utils/create_vectordb.py
```

This script:
- Reads schema files from `dataset/norp/schemas`
- Connects to the SQLite database to verify tables and get additional metadata
- Creates vector embeddings for each table
- Stores the embeddings in a Chroma database in the `rag/vectordb` directory

## Usage in Code

The `SchemaRAG` class provides methods to:

1. Retrieve relevant schemas for a query:
```python
schema_rag = SchemaRAG()
relevant_tables = schema_rag.get_relevant_tables("Show me all shootings in New York")
```

2. Get table information for a query:
```python
table_info = schema_rag.get_table_info_for_rag("Show me all shootings in New York")
```

3. Augment a prompt with schema context:
```python
base_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a SQL expert. Generate a SQL query for the following question."),
    ("human", "{question}")
])
augmented_prompt = schema_rag.augment_prompt("Show me all shootings in New York", base_prompt)
```

## API Usage

When making a query to the API, you can enable RAG by setting the `use_rag` flag:

```json
{
  "session_id": "123",
  "message": "Show me all shootings in New York",
  "message_type": "human",
  "use_rag": true
}
```

When `use_rag` is enabled, the system will:

1. Use the SchemaRAG component to retrieve relevant table schemas
2. Include only those schemas in the context for the LLM
3. Generate a more accurate SQL query based on the focused schema information

## Benefits

- **Reduced Prompt Size**: Only includes relevant tables, not the entire schema
- **Improved Accuracy**: Reduces hallucination of non-existent columns/tables
- **Better Performance**: LLM can focus on the relevant parts of the schema
- **Scalability**: Works well even with very large database schemas

## Implementation Details

The implementation consists of two main components:

1. `utils/create_vectordb.py`: Creates the vector database from schema files and the actual database
2. `rag/rag.py`: Contains the SchemaRAG class that handles retrieval and prompt augmentation 