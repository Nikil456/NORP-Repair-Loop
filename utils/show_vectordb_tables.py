#!/usr/bin/env python
"""
This script shows what tables would be ingested into the vector database
without actually creating the vector database.
"""

import os
import json
import sys
import mysql.connector
from mysql.connector import errorcode

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

def get_mysql_tables():
    """Get the list of tables from MySQL."""
    config = load_config()
    if not config:
        print("Failed to load configuration.")
        return []
    
    try:
        # Connect to the database
        db_url = config["db_url"]
        connection = mysql.connector.connect(
            host=db_url.split('@')[1].split('/')[0],
            user=config["db_username"],
            password=config["db_password"],
            database=db_url.split('/')[-1]
        )
        
        # Get table list
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        # Get row counts for each table
        table_info = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column information
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            column_info = []
            for col in columns:
                column_info.append({
                    "name": col[0],
                    "type": col[1]
                })
            
            table_info.append({
                "name": table_name,
                "row_count": row_count,
                "columns": column_info
            })
        
        cursor.close()
        connection.close()
        return table_info
    
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: Check your MySQL username and password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database doesn't exist")
        else:
            print(f"MySQL Error: {err}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    """Main function."""
    print("\n=== TABLES THAT WOULD BE INCLUDED IN VECTOR DATABASE ===")
    tables = get_mysql_tables()
    
    if not tables:
        print("No tables found or could not connect to the database.")
        return 1
    
    print(f"Found {len(tables)} tables in the MySQL database:")
    print("=" * 50)
    
    # Print table information
    for i, table in enumerate(tables, 1):
        print(f"{i}. {table['name']} ({table['row_count']} rows)")
        print(f"   Columns: {len(table['columns'])}")
        for col in table['columns'][:5]:  # Print first 5 columns only
            print(f"     - {col['name']} ({col['type']})")
        if len(table['columns']) > 5:
            print(f"     - ... and {len(table['columns']) - 5} more columns")
        print()
    
    print("=" * 50)
    print("Vector database would include schema information for all these tables")
    print("Each table would be represented as a document in the vector database")
    print("The vector database would be used for RAG (Retrieval-Augmented Generation)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 