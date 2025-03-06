"""
Test script for the SchemaRAG implementation.
This script demonstrates how the RAG system retrieves relevant schema information
and augments prompts for SQL generation.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag import SchemaRAG
from langchain_core.prompts import ChatPromptTemplate

def test_schema_retrieval():
    """Test schema retrieval functionality"""
    # Initialize SchemaRAG
    schema_rag = SchemaRAG()
    
    if not schema_rag.is_initialized():
        print("Vector database not found. Please run utils/create_vectordb.py first.")
        return
    
    # Test queries
    test_queries = [
        "Show me all shootings in New York",
        "What is the population of each state?",
        "Show me crime data for Atlanta",
        "What's the average household income by state?",
        "Which states have the highest number of people experiencing homelessness?",
        "Count the number of violent crimes in each city"
    ]
    
    for query in test_queries:
        print(f"\n\n=== Testing query: '{query}' ===\n")
        
        # Get relevant tables
        relevant_tables = schema_rag.get_relevant_tables(query)
        print(f"Relevant tables: {relevant_tables}")
        
        # Get table info for RAG
        table_info = schema_rag.get_table_info_for_rag(query)
        print(f"\nRetrieved schema information:\n{table_info[:500]}...")  # Show first 500 chars
        
        # Test prompt augmentation
        base_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a SQL expert. Generate a SQL query for the following question."),
            ("human", "{question}")
        ])
        
        augmented_prompt = schema_rag.augment_prompt(query, base_prompt)
        
        print("\nAugmented prompt:")
        # Get the first message (system message) from the augmented prompt
        first_message = augmented_prompt.messages[0]
        if hasattr(first_message, 'prompt'):
            # Get the template from the SystemMessagePromptTemplate
            template = first_message.prompt.template
            print(f"{template[:500]}...")  # Print the first 500 chars
        else:
            print("Could not extract template from message")

def main():
    """Main function to run tests"""
    # Check if vectordb exists
    vectordb_path = "rag/vectordb"
    if not os.path.exists(vectordb_path):
        print(f"Vector database not found at {vectordb_path}. Running create_vectordb.py first...")
        # Try to create the vector database
        try:
            from utils.create_vectordb import main as create_vectordb
            create_vectordb()
        except Exception as e:
            print(f"Error creating vector database: {e}")
            print("Please run 'python utils/create_vectordb.py' manually.")
            return
    
    # Run tests
    test_schema_retrieval()

if __name__ == "__main__":
    main() 