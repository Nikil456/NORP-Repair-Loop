#!/usr/bin/env python3
"""
Test Setup Script

This script verifies that the setup has been done correctly by checking:
1. The SQLite database exists and has tables
2. The RAG vector database exists
3. The config is set up correctly
"""

import os
import sys
import json
import sqlite3
import unittest

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSetup(unittest.TestCase):
    """Test class to verify the setup was done correctly"""
    
    def test_sqlite_database_exists(self):
        """Test that the SQLite database file exists"""
        db_path = "local_norp.db"
        self.assertTrue(os.path.exists(db_path), f"SQLite database does not exist at {db_path}")
    
    def test_sqlite_has_tables(self):
        """Test that the SQLite database has tables"""
        conn = sqlite3.connect("local_norp.db")
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        conn.close()
        
        # Convert to list of table names
        table_names = [table[0] for table in tables]
        
        # Check that we have some tables (at least the example ones)
        self.assertTrue(len(table_names) > 0, "No tables found in the SQLite database")
        print(f"Found {len(table_names)} tables: {', '.join(table_names)}")
    
    def test_vectordb_exists(self):
        """Test that the vector database directory exists"""
        vectordb_path = "rag/vectordb"
        self.assertTrue(os.path.exists(vectordb_path), f"Vector database directory does not exist at {vectordb_path}")
        
        # Check that the directory has some files (indicating it was created by ChromaDB)
        files = os.listdir(vectordb_path)
        non_readme_files = [f for f in files if f != "README.md"]
        
        self.assertTrue(len(non_readme_files) > 0, 
                        f"Vector database directory exists but has no files other than README.md: {vectordb_path}")
        print(f"Found {len(non_readme_files)} files in vector database directory")
    
    def test_config(self):
        """Test that the config is set up correctly for SQLite"""
        config_path = "config/config.json"
        self.assertTrue(os.path.exists(config_path), f"Config file does not exist at {config_path}")
        
        # Read the config
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Check that the database URL is set to SQLite
        self.assertTrue("db_url" in config, "db_url field missing from config")
        self.assertTrue(config["db_url"].startswith("sqlite:///"), 
                        f"db_url not set to SQLite. Got: {config['db_url']}")
        
        print(f"Config correctly set up with db_url: {config['db_url']}")
    
    def test_import_rag(self):
        """Test that the RAG module can be imported"""
        try:
            from rag.rag import SchemaRAG
            # Try to initialize SchemaRAG
            schema_rag = SchemaRAG()
            # Check if it's initialized (vector database exists and can be loaded)
            is_initialized = schema_rag.is_initialized()
            
            self.assertTrue(is_initialized, "SchemaRAG failed to initialize - vector database might not be properly set up")
            print("RAG module successfully imported and initialized")
        except ImportError as e:
            self.fail(f"Failed to import RAG module: {e}")
        except Exception as e:
            self.fail(f"Error initializing SchemaRAG: {e}")

if __name__ == "__main__":
    unittest.main() 