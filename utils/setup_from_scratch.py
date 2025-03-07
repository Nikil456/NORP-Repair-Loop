#!/usr/bin/env python3
"""
Setup From Scratch Script

This script performs a complete setup of the application:
1. Check if MySQL server is running, try to start it if not
2. Create MySQL database using the configuration
3. Ingest all data into the MySQL database using populate_sql.py
4. Set up RAG (Retrieval-Augmented Generation) system
5. Set up Redis
6. Run tests to verify everything is working

Usage:
    python utils/setup_from_scratch.py [--mock-mysql]
"""

import os
import sys
import json
import shutil
import subprocess
import importlib.util
import argparse
from pathlib import Path
import mysql.connector
from mysql.connector import errorcode
import time
import re

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global flag for mock mode
MOCK_MYSQL = False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Setup the application from scratch.')
    parser.add_argument('--mock-mysql', action='store_true', 
                      help='Run in mock mode without an actual MySQL server')
    parser.add_argument('--force', action='store_true',
                      help='Force setup even if it might overwrite existing data')
    parser.add_argument('--skip-tests', action='store_true',
                      help='Skip running tests after setup')
    return parser.parse_args()

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
    """Update configuration to use MySQL."""
    try:
        # Configuration should already be set for MySQL in config.json
        # But we ensure it's still in the correct format
        if not config["db_url"].startswith("mysql+mysqlconnector://"):
            print("Ensuring MySQL configuration is set...")
            config["db_url"] = "mysql+mysqlconnector://root:password@localhost/norp_db"
            config["db_username"] = "root"
            config["db_password"] = "password"
            
            # Write updated config back to file
            config_path = "config/config.json"
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            print("Configuration updated to use MySQL")
        
        return True
    except Exception as e:
        print(f"Error updating config: {e}")
        return False

def is_mysql_running(config):
    """Check if MySQL server is running and accessible."""
    if MOCK_MYSQL:
        print("[MOCK] Pretending MySQL server is running")
        return True
        
    try:
        # Parse the connection string to get host and port
        connection_string = config["db_url"]
        # Extract host from the connection string
        host = connection_string.split('@')[1].split('/')[0]
        # Handle case where host might include port
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        else:
            port = 3306  # Default MySQL port
        
        # Try to connect to MySQL server (without specifying a database)
        mysql.connector.connect(
            user=config["db_username"],
            password=config["db_password"],
            host=host,
            port=port,
            connection_timeout=5
        )
        print(f"MySQL server is running at {host}:{port}")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL server is not running or not accessible: {err}")
        return False
    except Exception as e:
        print(f"Error checking MySQL server: {e}")
        return False

def start_mysql_server():
    """Try to start MySQL server using various methods."""
    if MOCK_MYSQL:
        print("[MOCK] Pretending to start MySQL server")
        return True
        
    try:
        # Try different methods to start MySQL server
        
        # 1. Try using systemctl (Linux)
        print("Attempting to start MySQL server using systemctl...")
        result = subprocess.run(["systemctl", "start", "mysql"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Started MySQL server using systemctl")
            return True
        
        # 2. Try using service (some Linux distributions)
        print("Attempting to start MySQL server using service...")
        result = subprocess.run(["service", "mysql", "start"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Started MySQL server using service")
            return True
        
        # 3. Try using mysqld directly
        print("Attempting to start MySQL server directly...")
        result = subprocess.run(["mysqld", "--user=mysql"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Started MySQL server using mysqld directly")
            return True
            
        # 4. Try macOS specific command
        print("Attempting to start MySQL server using brew services (macOS)...")
        result = subprocess.run(["brew", "services", "start", "mysql"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Started MySQL server using brew services")
            return True
        
        # If we get here, all methods failed
        print("ERROR: Could not start MySQL server with any available method.")
        print("Make sure MySQL is installed on your system.")
        print("System requirements:")
        print("  - MySQL server must be installed")
        print("  - MySQL server must be properly configured")
        print("Installation instructions:")
        print("  - Ubuntu/Debian: sudo apt-get install mysql-server")
        print("  - CentOS/RHEL: sudo yum install mysql-server")
        print("  - macOS: brew install mysql && brew services start mysql")
        raise Exception("MySQL server is required but could not be started")
        
    except Exception as e:
        print(f"ERROR: Failed to start MySQL server: {e}")
        raise Exception("MySQL server is required but could not be started") from e

def clean_databases():
    """Clean existing databases before setup."""
    try:
        print("Cleaning existing databases...")
        
        # Delete vector database
        vectordb_path = "data/vectordb"
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
        
        if MOCK_MYSQL:
            print("[MOCK] Pretending to drop and create MySQL database")
            return True
            
        config = load_config()
        if not config:
            print("Failed to load configuration. Aborting setup.")
            return False
        
        try:
            # Extract database name from connection string
            db_url = config["db_url"]
            db_name = db_url.split('/')[-1]
            
            # Check if MySQL is running
            if not is_mysql_running(config):
                print("MySQL server is not running. Attempting to start it...")
                if not start_mysql_server():
                    print("Failed to start MySQL server. Please start it manually.")
                    return False
            
            # Get connection info
            connection_string = config["db_url"]
            # Extract host from the connection string
            host = connection_string.split('@')[1].split('/')[0]
            # Handle case where host might include port
            if ':' in host:
                host, port = host.split(':')
                port = int(port)
            else:
                port = 3306  # Default MySQL port
            
            # Connect to MySQL server (without specifying database)
            cnx = mysql.connector.connect(
                user=config["db_username"],
                password=config["db_password"],
                host=host,
                port=port
            )
            cursor = cnx.cursor()
            
            # Drop the database if it exists
            try:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                print(f"Dropped existing MySQL database: {db_name}")
            except mysql.connector.Error as err:
                print(f"Error dropping database: {err}")
            
            # Create the database
            try:
                cursor.execute(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"Created MySQL database: {db_name}")
            except mysql.connector.Error as err:
                print(f"Error creating database: {err}")
                return False
            
            # Close connection
            cursor.close()
            cnx.close()
            
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Access denied: Check your MySQL username and password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database doesn't exist")
            else:
                print(f"MySQL Error: {err}")
            return False
        
        return True
    except Exception as e:
        print(f"Error cleaning databases: {e}")
        return False

def ingest_data():
    """Ingest all tables into the MySQL database using populate_sql.py."""
    global ingest_cmd
    
    if MOCK_MYSQL:
        print("[MOCK] Pretending to ingest data into MySQL database")
        print("[MOCK] This would normally run the populate_sql.py script")
        print("[MOCK] In a real setup, this step is CRITICAL for the application to function")
        # Create an empty file to simulate the database
        with open("mock_norp_db.txt", "w") as f:
            f.write("This is a mock database file to simulate successful data ingestion\n")
        return True
        
    try:
        print("\n=== MYSQL DATABASE INGESTION ===")
        print("Ingesting all tables into the MySQL database...")
        
        # Use populate_sql.py to ingest the data
        populate_sql_script = "utils/populate_sql.py"
        if os.path.exists(populate_sql_script):
            # Use the command prepared in main if available
            cmd = ingest_cmd if 'ingest_cmd' in globals() else [sys.executable, populate_sql_script]
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("\n=== DATA INGESTION COMPLETED SUCCESSFULLY ===")
                
                # Verify tables were created
                config = load_config()
                if not config:
                    print("Failed to load configuration for table verification.")
                    return False
                
                try:
                    # Connect to the database
                    db_url = config["db_url"]
                    connection = mysql.connector.connect(
                        host=db_url.split('@')[1].split('/')[0],
                        user=config["db_username"],
                        password=config["db_password"],
                        database=db_url.split('/')[-1]
                    )
                    
                    # Check for critical tables
                    cursor = connection.cursor()
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    
                    if not tables:
                        print("ERROR: No tables were created during ingestion.")
                        return False
                    
                    print(f"\n=== SUCCESSFULLY INGESTED {len(tables)} TABLES INTO MYSQL DATABASE ===")
                    print("The following tables are now available in the database:")
                    print("=" * 50)
                    for i, table in enumerate(tables, 1):
                        print(f"{i}. {table[0]}")
                    print("=" * 50)
                    
                    # Get row counts for each table
                    print("\nRow counts for each table:")
                    print("=" * 50)
                    for table in tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        print(f"{table_name}: {row_count} rows")
                    print("=" * 50)
                    
                    return True
                except mysql.connector.Error as err:
                    print(f"Failed to verify tables: {err}")
                    return False
            else:
                print(f"Error during data ingestion, exit code: {result.returncode}")
                print("STDOUT:")
                print(result.stdout)
                print("STDERR:")
                print(result.stderr)
                return False
        else:
            print(f"ERROR: Script {populate_sql_script} not found.")
            raise FileNotFoundError(f"Critical file {populate_sql_script} is missing")
    except Exception as e:
        print(f"Error ingesting data: {e}")
        return False

def setup_rag():
    """Set up the RAG system with vector database."""
    global rag_cmd
    
    if MOCK_MYSQL:
        print("[MOCK] Pretending to set up vector database")
        with open("mock_vectordb.txt", "w") as f:
            f.write("This is a mock vector database file\n")
        return True
    
    try:
        print("\n=== VECTOR DATABASE SETUP ===")
        print("Setting up vector database for retrieval-augmented generation...")
        
        # Ensure vector database directory exists
        vectordb_path = "data/vectordb"
        os.makedirs(vectordb_path, exist_ok=True)
        
        # Run the create_vectordb.py script
        create_vectordb_script = "utils/create_vectordb.py"
        if os.path.exists(create_vectordb_script):
            # Use the command prepared in main if available
            cmd = rag_cmd if 'rag_cmd' in globals() else [sys.executable, create_vectordb_script, "--force", "--verbose"]
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Display all output for debugging
            print("\nOutput from vector database creation:")
            print("=" * 50)
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print("=" * 50)
            
            if result.returncode == 0:
                print("\n=== VECTOR DATABASE CREATED SUCCESSFULLY ===")
                
                # Check if vectordb was created properly
                if os.path.exists(vectordb_path) and os.listdir(vectordb_path):
                    print(f"Vector database directory populated at {vectordb_path}")
                    # Count files to verify
                    file_count = sum(1 for _ in os.listdir(vectordb_path) if not _.startswith('.'))
                    print(f"Vector database contains {file_count} files/directories")
                    
                    # List the tables that were indexed in the vector database
                    # This is based on output captured in stdout
                    table_pattern = re.compile(r"Created document for table (\w+)")
                    tables = table_pattern.findall(result.stdout)
                    if tables:
                        print("\nThe following tables were indexed in the vector database:")
                        print("=" * 50)
                        for i, table in enumerate(sorted(set(tables)), 1):
                            print(f"{i}. {table}")
                        print("=" * 50)
                    
                    return True
                else:
                    print(f"ERROR: Vector database directory {vectordb_path} is empty after creation")
                    return False
            else:
                print(f"ERROR: Failed to create vector database, exit code: {result.returncode}")
                return False
        else:
            print(f"ERROR: Script {create_vectordb_script} not found")
            raise FileNotFoundError(f"Critical file {create_vectordb_script} is missing")
    except Exception as e:
        print(f"ERROR: Failed to set up vector database: {e}")
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
    """Run all tests to verify the system is set up correctly."""
    if MOCK_MYSQL:
        print("[MOCK] Pretending to run tests")
        return True
        
    try:
        print("Running all tests to verify setup...")
        tests_dir = "tests"
        
        if not os.path.exists(tests_dir):
            print(f"ERROR: Tests directory '{tests_dir}' not found")
            return False
            
        # Find all test files
        test_files = []
        for root, _, files in os.walk(tests_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        
        if not test_files:
            print(f"ERROR: No test files found in '{tests_dir}'")
            return False
            
        print(f"Found {len(test_files)} test files to run")
        
        # Run each test
        success = True
        failed_tests = []
        passed_tests = []
        
        for test_file in test_files:
            print(f"Running test: {test_file}")
            result = subprocess.run([sys.executable, "-m", "pytest", test_file, "-v"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Test {test_file} passed")
                passed_tests.append(test_file)
            else:
                print(f"❌ Test {test_file} FAILED, exit code: {result.returncode}")
                print("Test output:")
                print(result.stdout)
                print("Test errors:")
                print(result.stderr)
                failed_tests.append(test_file)
                success = False
        
        # Print summary
        print("\n=== TEST SUMMARY ===")
        print(f"Total tests: {len(test_files)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if failed_tests:
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test}")
        
        return success
    except Exception as e:
        print(f"ERROR: Failed to run tests: {e}")
        return False

def main():
    """Main function that orchestrates the setup process."""
    global MOCK_MYSQL
    
    # Parse command line arguments
    args = parse_arguments()
    MOCK_MYSQL = args.mock_mysql
    
    if MOCK_MYSQL:
        print("=== RUNNING IN MOCK MODE ===")
        print("This mode simulates the setup process without requiring an actual MySQL server.")
        print("For a real deployment, run without the --mock-mysql flag and ensure MySQL is installed.")
        print("=============================================")
    
    if args.force:
        print("=== RUNNING IN FORCE MODE ===")
        print("This will overwrite existing data without confirmation.")
        print("=============================================")
    
    print("Starting setup from scratch...")
    
    try:
        # Load config
        config = load_config()
        if not config:
            print("Failed to load configuration. Aborting setup.")
            return False
        
        # Update config for MySQL
        if not update_config(config):
            print("Failed to update configuration. Aborting setup.")
            return False
        
        # Check if MySQL server is running - CRITICAL REQUIREMENT
        if not is_mysql_running(config):
            print("MySQL server is not running. Attempting to start it...")
            # This will throw an exception if MySQL cannot be started
            start_mysql_server()
        
        # Clean existing databases
        if not clean_databases():
            print("Failed to clean databases. Aborting setup.")
            return False
        
        # Ingest data using populate_sql.py - THIS IS A CRITICAL STEP
        print("Starting data ingestion into MySQL (CRITICAL STEP)...")
        ingest_cmd = [sys.executable, "utils/populate_sql.py"]
        if args.force or True:  # Always drop tables for clean setup
            ingest_cmd.append("--drop-tables")
        
        if not ingest_data():
            print("Failed to ingest data into MySQL. Aborting setup.")
            return False
        
        # Set up vector database (RAG)
        print("Setting up vector database...")
        rag_cmd = [sys.executable, "utils/create_vectordb.py"]
        if args.force:
            rag_cmd.append("--force")
            
        if not setup_rag():
            print("Failed to set up vector database. Aborting setup.")
            return False
        
        # Set up Redis
        print("Setting up Redis...")
        if not setup_redis():
            print("WARNING: Failed to set up Redis. Continuing with setup.")
        
        # Run all tests if not skipped
        if not args.skip_tests:
            print("Running all tests to verify setup...")
            if not run_tests():
                print("Some tests failed. The setup may not be complete.")
                return False
        else:
            print("Skipping tests as requested with --skip-tests")
        
        if MOCK_MYSQL:
            print("\n=== MOCK SETUP COMPLETED SUCCESSFULLY ===")
            print("This was a simulation of the setup process.")
            print("For a real deployment:")
            print("1. Install and start a MySQL server")
            print("2. Run this script without the --mock-mysql flag")
        else:
            print("=== SETUP COMPLETED SUCCESSFULLY ===")
            print("MySQL server is running")
            print("All tables have been ingested into MySQL")
            print("Vector database has been set up")
            if not args.skip_tests:
                print("All tests have passed")
            else:
                print("Tests were skipped")
        
        return True
    
    except Exception as e:
        print(f"\n=== SETUP FAILED ===")
        print(f"Error during setup: {e}")
        print("Please fix the issues and try again.")
        return False

if __name__ == "__main__":
    sys.exit(main()) 