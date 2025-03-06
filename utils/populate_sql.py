#!/usr/bin/env python3
import os
import json
import csv
import sqlite3
from sqlalchemy import create_engine, text
import pandas as pd
import re
import argparse
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Populate SQL database with CSV data.')
    parser.add_argument('--drop-tables', action='store_true', help='Drop existing tables before creating them')
    parser.add_argument('--table', type=str, help='Process only a specific table')
    return parser.parse_args()

def load_config():
    """Load database configuration from config file."""
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    return config

def get_create_table_statements():
    """Read all schema files and get CREATE TABLE statements."""
    schemas_dir = 'dataset/norp/schemas'
    create_statements = {}
    
    for schema_file in os.listdir(schemas_dir):
        if schema_file.endswith('.txt'):
            table_name = os.path.splitext(schema_file)[0]
            with open(os.path.join(schemas_dir, schema_file), 'r') as f:
                create_statement = f.read().strip()
                create_statements[table_name] = create_statement
    
    return create_statements

def get_csv_files():
    """Get all CSV files in the dataset directory."""
    csv_dir = 'dataset/norp/csv'
    csv_files = {}
    
    for csv_file in os.listdir(csv_dir):
        if csv_file.endswith('.csv'):
            table_name = os.path.splitext(csv_file)[0]
            csv_files[table_name] = os.path.join(csv_dir, csv_file)
    
    return csv_files

def clean_column_names(df):
    """Clean column names to match SQL schema format."""
    # Replace spaces with underscores
    df.columns = [col.replace(' ', '_') for col in df.columns]
    
    # Replace special characters that cause issues
    df.columns = [col.replace('#', 'Number') for col in df.columns]
    df.columns = [col.replace('-', '_') for col in df.columns]
    df.columns = [col.replace('&', 'And') for col in df.columns]
    df.columns = [col.replace('%', 'Percent') for col in df.columns]
    df.columns = [col.replace('(', '') for col in df.columns]
    df.columns = [col.replace(')', '') for col in df.columns]
    df.columns = [col.replace('.', '') for col in df.columns]
    
    return df

def extract_column_names_from_schema(create_statement):
    """Extract column names from CREATE TABLE statement."""
    # Find the part between the parentheses
    match = re.search(r'\((.*)\)', create_statement, re.DOTALL)
    if not match:
        return []
    
    # Split by commas, but avoid splitting inside parentheses
    columns_part = match.group(1).strip()
    columns = []
    current_column = ""
    parenthesis_level = 0
    
    for char in columns_part:
        if char == '(':
            parenthesis_level += 1
            current_column += char
        elif char == ')':
            parenthesis_level -= 1
            current_column += char
        elif char == ',' and parenthesis_level == 0:
            columns.append(current_column.strip())
            current_column = ""
        else:
            current_column += char
    
    if current_column.strip():
        columns.append(current_column.strip())
    
    # Extract just the column names (before the data type)
    column_names = []
    for column in columns:
        parts = column.strip().split()
        if parts:
            # Remove any backticks or quotes
            col_name = parts[0].strip('`"\'')
            column_names.append(col_name)
    
    return column_names

def ensure_db_dir_exists(db_url):
    """Ensure the directory for the database file exists."""
    if db_url.startswith('sqlite:///'):
        # Extract the file path from the SQLite URL
        db_path = db_url.replace('sqlite:///', '')
        
        # Create parent directories if they don't exist
        dir_path = os.path.dirname(db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")

def drop_table(conn, table_name):
    """Drop a table if it exists."""
    try:
        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        conn.commit()
        print(f"Dropped table: {table_name}")
    except Exception as e:
        print(f"Error dropping table {table_name}: {str(e)}")

def process_table(conn, table_name, create_statement, csv_path):
    """Process a single table - create and populate it."""
    try:
        # Create the table
        conn.execute(text(create_statement))
        conn.commit()
        print(f"Created table: {table_name}")
        
        if csv_path:
            print(f"Populating table {table_name} from {csv_path}")
            
            try:
                # Get the expected column names from the schema
                schema_columns = extract_column_names_from_schema(create_statement)
                
                # Read CSV file with pandas
                df = pd.read_csv(csv_path)
                
                # Clean column names
                df = clean_column_names(df)
                
                # Align DataFrame columns with schema columns if possible
                if len(schema_columns) > 0 and len(df.columns) == len(schema_columns):
                    df.columns = schema_columns
                
                # For large files, import in chunks
                file_size = os.path.getsize(csv_path)
                
                if file_size > 10 * 1024 * 1024:  # if file is larger than 10MB
                    chunk_size = 10000  # Adjust based on your memory constraints
                    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size)):
                        # Clean column names for each chunk
                        chunk = clean_column_names(chunk)
                        
                        # Align DataFrame columns with schema columns if possible
                        if len(schema_columns) > 0 and len(chunk.columns) == len(schema_columns):
                            chunk.columns = schema_columns
                        
                        if i == 0:
                            # Print first few column names for debugging
                            print(f"  CSV columns: {list(chunk.columns)[:5]}...")
                            
                        chunk.to_sql(table_name, conn, if_exists='append', index=False)
                        print(f"  Imported chunk {i+1} of {table_name}")
                else:
                    # Print first few column names for debugging
                    print(f"  CSV columns: {list(df.columns)[:5]}...")
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                print(f"Successfully populated {table_name}")
            except Exception as e:
                print(f"Error populating {table_name}: {str(e)}")
                # Try direct SQLite approach for problematic tables
                try:
                    print(f"  Trying direct SQLite import for {table_name}")
                    # Get SQLite connection from engine
                    sqlite_conn = conn.connection
                    cursor = sqlite_conn.cursor()
                    
                    # Drop table if it exists, then create it again
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                    cursor.execute(create_statement)
                    sqlite_conn.commit()
                    
                    # Import CSV directly using SQLite's import
                    with open(csv_path, 'r') as f:
                        reader = csv.reader(f)
                        header = next(reader)  # Skip header
                        
                        # Create SQL insert command with placeholders
                        placeholders = ', '.join(['?' for _ in range(len(schema_columns))])
                        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                        
                        # Batch insert in chunks
                        batch_size = 5000
                        batch = []
                        
                        for i, row in enumerate(reader):
                            batch.append(row)
                            
                            if len(batch) >= batch_size:
                                cursor.executemany(insert_sql, batch)
                                sqlite_conn.commit()
                                print(f"  Imported {len(batch)} rows")
                                batch = []
                        
                        # Insert any remaining rows
                        if batch:
                            cursor.executemany(insert_sql, batch)
                            sqlite_conn.commit()
                            print(f"  Imported {len(batch)} remaining rows")
                    
                    print(f"Successfully populated {table_name} using direct SQLite import")
                except Exception as inner_e:
                    print(f"  Direct import also failed: {str(inner_e)}")
        else:
            print(f"Warning: No CSV file found for table {table_name}")
    except Exception as e:
        print(f"Error processing table {table_name}: {str(e)}")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config()
    db_url = config['db_url']
    
    # Ensure database directory exists
    ensure_db_dir_exists(db_url)
    
    # Create database engine
    engine = create_engine(db_url)
    
    # Get schema statements and CSV files
    create_statements = get_create_table_statements()
    csv_files = get_csv_files()
    
    # Process tables
    with engine.connect() as conn:
        if args.table:
            # Process only the specified table
            if args.table in create_statements:
                if args.drop_tables:
                    drop_table(conn, args.table)
                csv_path = csv_files.get(args.table)
                process_table(conn, args.table, create_statements[args.table], csv_path)
            else:
                print(f"Error: Table '{args.table}' not found in schema files")
        else:
            # Process all tables
            for table_name, create_statement in create_statements.items():
                if args.drop_tables:
                    drop_table(conn, table_name)
                csv_path = csv_files.get(table_name)
                process_table(conn, table_name, create_statement, csv_path)
    
    print("Database setup complete!")

if __name__ == "__main__":
    main()
