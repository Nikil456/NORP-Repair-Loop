# RAG-based Schema Context for SQL Generation

This module implements a Retrieval-Augmented Generation (RAG) pipeline to provide relevant database schema context for SQL query generation.

## Overview

The RAG pipeline provides the following benefits:

1. **Selective Schema Context**: Instead of sending the entire database schema to the LLM, RAG retrieves only the most relevant tables based on the user's query, reducing token usage and improving SQL generation.

2. **Reduced Hallucination**: By providing accurate schema information, the LLM is less likely to hallucinate column or table names that don't exist.

3. **Improved Query Accuracy**: The LLM receives detailed information about table structures and relationships, leading to more accurate SQL queries.

## Components

The RAG implementation consists of the following components:

1. **Vector Database Creation (`utils/create_vectordb.py`)**: 
   - Creates a ChromaDB instance with embedded schema documents
   - Each document represents a database table with its columns, types, relationships, and description
   - Uses SentenceTransformer for embeddings

2. **Retrieval and Augmentation (`rag/vector_database/rag.py`)**: 
   - Handles retrieval of relevant schema information based on user queries
   - Formats retrieved schema information for the LLM
   - Integrates with the existing SQL generation pipeline

## Usage

### Setup

Before using the RAG pipeline, you need to create the vector database:

```bash
python utils/create_vectordb.py
```

### API Usage

When making a query to the API, you can enable RAG by setting the `use_rag` flag:

```json
{
  "session_id": "123",
  "question": "Show me all shootings in Texas",
  "message_type": "human",
  "use_rag": true
}
```

When `use_rag` is enabled, the system will:
1. Embed the user's query
2. Retrieve the most relevant schema information
3. Add this information to the context for the LLM
4. Generate an SQL query based on the augmented context 