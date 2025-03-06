# Vector Database for Schema RAG

This directory contains the Chroma vector database used for schema retrieval in the RAG system.

## Contents

When the vector database is initialized (by running `python utils/create_vectordb.py`), this directory will contain:
- Vector embeddings for each table schema
- Metadata about the tables and columns
- Configuration for the Chroma database

## Important Notes

- Do not manually modify these files as it may corrupt the database
- If schema changes are made to the underlying database, regenerate this vector database by running `python utils/create_vectordb.py` again
- The vector database uses the sentence-transformers/paraphrase-MiniLM-L3-v2 model for embeddings 