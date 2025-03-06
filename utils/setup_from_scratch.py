#!/usr/bin/env python3
"""
Setup From Scratch Script

This script performs a complete setup of the application:
1. Delete existing SQLite database and vector database
2. Set up a new SQLite database using the configuration
3. Ingest all data into the new database using populate_sql.py
4. Set up RAG (Retrieval-Augmented Generation) system
5. Set up Redis
6. Run all tests to verify everything is working

Usage:
    python utils/setup_from_scratch.py
"""

import os
import sys
import json
import shutil
import sqlite3
import subprocess
import importlib.util
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config():
    """Load configuration from config file."""
    try:
        config_path = "config/config.json"
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def update_config(config):
    """Update configuration to use SQLite."""
    try:
        # Update config to use SQLite
        config["db_url"] = "sqlite:///local_norp.db"
        config["db_username"] = ""
        config["db_password"] = ""
        
        # Write updated config back to file
        config_path = "config/config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        print("Configuration updated to use SQLite")
        return True
    except Exception as e:
        print(f"Error updating config: {e}")
        return False

def clean_databases():
    """Delete existing SQLite database and vector database."""
    try:
        # Delete SQLite database
        db_path = "local_norp.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Deleted existing SQLite database: {db_path}")
        
        # Delete vector database
        vectordb_path = "rag/vectordb"
        if os.path.exists(vectordb_path):
            # Keep the README.md file
            readme_path = os.path.join(vectordb_path, "README.md")
            readme_content = None
            if os.path.exists(readme_path):
                with open(readme_path, "r") as f:
                    readme_content = f.read()
            
            # Delete the directory
            shutil.rmtree(vectordb_path)
            print(f"Deleted existing vector database: {vectordb_path}")
            
            # Recreate the directory
            os.makedirs(vectordb_path, exist_ok=True)
            
            # Restore the README.md file
            if readme_content:
                with open(readme_path, "w") as f:
                    f.write(readme_content)
            
        return True
    except Exception as e:
        print(f"Error cleaning databases: {e}")
        return False

def ingest_data():
    """Ingest data into the database using populate_sql.py."""
    try:
        print("Ingesting data into the database...")
        
        # Use populate_sql.py to ingest the data
        populate_sql_script = "utils/populate_sql.py"
        if os.path.exists(populate_sql_script):
            print(f"Running {populate_sql_script} to ingest data...")
            result = subprocess.run([sys.executable, populate_sql_script, "--drop-tables"], text=True)
            if result.returncode == 0:
                print("Data ingestion completed successfully")
                return True
            else:
                print(f"Error during data ingestion, exit code: {result.returncode}")
                return False
        else:
            print(f"Script {populate_sql_script} not found.")
            return False
    except Exception as e:
        print(f"Error ingesting data: {e}")
        return False

def setup_rag():
    """Set up the RAG system."""
    try:
        print("Setting up RAG (Retrieval-Augmented Generation) system...")
        
        # Run the create_vectordb.py script
        create_vectordb_script = "utils/create_vectordb.py"
        if os.path.exists(create_vectordb_script):
            print(f"Running {create_vectordb_script} to create vector database...")
            result = subprocess.run([sys.executable, create_vectordb_script], text=True)
            if result.returncode == 0:
                print("Vector database created successfully")
                return True
            else:
                print(f"Error creating vector database, exit code: {result.returncode}")
                return False
        else:
            print(f"Script {create_vectordb_script} not found.")
            return False
    except Exception as e:
        print(f"Error setting up RAG: {e}")
        return False

def setup_redis():
    """Set up Redis if needed."""
    try:
        print("Checking Redis setup...")
        
        # Try to import redis
        try:
            import redis
            print("Redis package is installed")
            
            # Try to connect to Redis
            config = load_config()
            if config:
                host = config.get("redis_host_url", "localhost")
                port = int(config.get("redis_port", 6379))
                password = config.get("redis_password", None)
                
                r = redis.Redis(host=host, port=port, password=password)
                r.ping()
                print(f"Successfully connected to Redis at {host}:{port}")
                return True
            else:
                print("Could not load config for Redis connection")
                return False
        except ImportError:
            print("Redis package is not installed. Install it with: pip install redis")
            return False
        except redis.exceptions.ConnectionError:
            print("Could not connect to Redis. Make sure Redis server is running.")
            print("You can start Redis locally or use Docker:")
            print("  docker run --name redis -p 6379:6379 -d redis")
            return False
    except Exception as e:
        print(f"Error setting up Redis: {e}")
        return False

def run_tests():
    """Run tests to verify the setup."""
    try:
        print("Running tests to verify setup...")
        
        # Find all test files
        test_files = []
        for root, dirs, files in os.walk("tests"):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        
        if not test_files:
            print("No test files found.")
            return False
        
        # Run each test file
        success = True
        for test_file in test_files:
            print(f"\nRunning test: {test_file}")
            # Remove capture_output=True to show all test output
            result = subprocess.run([sys.executable, test_file], text=True)
            if result.returncode == 0:
                print(f"Test {test_file} passed")
            else:
                print(f"Test {test_file} failed, exit code: {result.returncode}")
                success = False
        
        return success
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    """Main function that orchestrates the setup process."""
    print("Starting setup from scratch...")
    
    # Load config
    config = load_config()
    if not config:
        print("Failed to load configuration. Aborting setup.")
        return False
    
    # Update config to use SQLite
    if not update_config(config):
        print("Failed to update configuration. Aborting setup.")
        return False
    
    # Clean existing databases
    if not clean_databases():
        print("Failed to clean databases. Aborting setup.")
        return False
    
    # Ingest data using populate_sql.py
    if not ingest_data():
        print("Failed to ingest data. Aborting setup.")
        return False
    
    # Set up RAG
    if not setup_rag():
        print("Failed to set up RAG. Aborting setup.")
        return False
    
    # Set up Redis (optional, continue if it fails)
    setup_redis()
    
    # Run tests
    if not run_tests():
        print("Some tests failed. The setup may not be complete.")
        return False
    
    print("Setup completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 