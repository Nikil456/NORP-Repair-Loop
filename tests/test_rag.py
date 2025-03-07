"""
Test script for the SchemaRAG implementation.
This script demonstrates how the RAG system retrieves relevant schema information
and augments prompts for SQL generation.
"""

import os
import sys
import logging
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag import SchemaRAG
from langchain_core.prompts import ChatPromptTemplate

# Setup logger
def setup_logger():
    """Setup and return a logger that writes to a file"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a logger
    logger = logging.getLogger("rag_test_logger")
    logger.setLevel(logging.INFO)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create a file handler with a timestamp in the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(os.path.join(logs_dir, f"rag_test_errors_{timestamp}.log"))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    
    return logger

def test_schema_retrieval(logger):
    """Test schema retrieval functionality"""
    # Initialize SchemaRAG
    schema_rag = SchemaRAG()
    
    if not schema_rag.is_initialized():
        error_msg = "Vector database not found. Please run utils/create_vectordb.py first."
        logger.error(error_msg)
        print(error_msg)
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
    
    failed_queries = 0
    
    for query in test_queries:
        print(f"\n\n=== Testing query: '{query}' ===\n")
        logger.info(f"Testing query: '{query}'")
        
        try:
            # Get relevant tables
            relevant_tables = schema_rag.get_relevant_tables(query)
            print(f"Relevant tables: {relevant_tables}")
            
            if not relevant_tables:
                error_msg = f"Failed to retrieve relevant tables for query: '{query}'"
                logger.error(error_msg)
                failed_queries += 1
                continue
            
            # Get table info for RAG
            table_info = schema_rag.get_table_info_for_rag(query)
            print(f"\nRetrieved schema information:\n{table_info[:500]}...")  # Show first 500 chars
            
            if not table_info:
                error_msg = f"Failed to retrieve table information for query: '{query}'"
                logger.error(error_msg)
                failed_queries += 1
                continue
            
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
                error_msg = f"Could not extract template from message for query: '{query}'"
                logger.error(error_msg)
                print(error_msg)
                failed_queries += 1
                
        except Exception as e:
            error_msg = f"Error processing query '{query}': {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            failed_queries += 1
    
    # Log summary
    if failed_queries > 0:
        logger.info(f"Test completed with {failed_queries} failed queries out of {len(test_queries)}")
    else:
        logger.info("All queries processed successfully")

def main():
    """Main function to run tests"""
    # Setup logger
    logger = setup_logger()
    logger.info("Starting RAG test")
    
    # Check if vectordb exists
    vectordb_path = "rag/vectordb"
    if not os.path.exists(vectordb_path):
        error_msg = f"Vector database not found at {vectordb_path}. Running create_vectordb.py first..."
        logger.warning(error_msg)
        print(error_msg)
        
        # Try to create the vector database
        try:
            from utils.create_vectordb import main as create_vectordb
            create_vectordb()
        except Exception as e:
            error_msg = f"Error creating vector database: {e}"
            logger.error(error_msg)
            print(error_msg)
            print("Please run 'python utils/create_vectordb.py' manually.")
            return
    
    # Run tests
    test_schema_retrieval(logger)
    logger.info("RAG test completed")

if __name__ == "__main__":
    main() 