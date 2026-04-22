import csv
import pandas as pd
import mysql.connector
from mysql.connector import Error
import re
from tqdm import tqdm
import argparse
import time
import os
import sys

# Add the project root to the Python path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.abspath(__file__))))
from utils.column_utils import clean_column_name, clean_dataframe_columns

def connect_to_mysql(host="localhost", user="root", password="root", database="norp_db"):
    """Establishes connection to MySQL database"""
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                connection_timeout=60
            )
            if connection.is_connected():
                return connection
            else:
                attempt += 1
                if attempt < max_attempts:
                    print(f"Connection attempt {attempt} failed. Retrying in 3 seconds...")
                    time.sleep(3)
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            attempt += 1
            if attempt < max_attempts:
                print(f"Connection attempt {attempt} failed. Retrying in 3 seconds...")
                time.sleep(3)
    
    print(f"Failed to connect to MySQL after {max_attempts} attempts.")
    return None

def check_connection(connection):
    """Check if the connection is still valid, reconnect if needed"""
    try:
        if connection is None or not connection.is_connected():
            return None
        # Test the connection with a simple query
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()
        cursor.close()
        return connection
    except Error:
        return None

def get_all_tables(connection):
    """Get a list of all tables in the database"""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        return tables
    except Error as e:
        print(f"Error getting tables: {e}")
        return []


def test_query(connection, query, specified_tables, all_db_tables, verbose=False, conn_params=None):
    """
    Test if a SQL query can be executed without errors
    Returns (success_bool, message)
    """
    # Check for us_shootings table - special handling due to known connection issues
    is_us_shootings_query = any('us_shootings' in table.lower() for table in specified_tables)

    # Make sure connection is active or try to reconnect
    connection_retry_attempts = 5 if is_us_shootings_query else 3  # More retries for us_shootings
    
    # First connection check, with retry logic
    for attempt in range(connection_retry_attempts):
        if connection is None or not connection.is_connected():
            if verbose:
                print(f"Connection check failed on attempt {attempt+1}, attempting to reconnect...")
            
            # Close the connection if it exists but is not connected
            if connection is not None:
                try:
                    connection.close()
                    if verbose:
                        print("Closed existing connection.")
                except:
                    pass  # Ignore errors when closing an already problematic connection
            
            # Create a new connection
            if conn_params:
                connection = connect_to_mysql(**conn_params)
            else:
                connection = connect_to_mysql()
            
            # If still no connection after attempt, wait and try again if not last attempt
            if connection is None or not connection.is_connected():
                if attempt < connection_retry_attempts - 1:
                    # Longer wait time for us_shootings queries
                    wait_time = 8 * (attempt + 1) if is_us_shootings_query else 5 * (attempt + 1)
                    if verbose:
                        print(f"Connection still unavailable. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    return False, "MySQL Connection not available after multiple reconnection attempts."
            else:
                if verbose:
                    print("Successfully reconnected to MySQL.")
                break
    
    # Final connection check before proceeding
    if connection is None or not connection.is_connected():
        return False, "MySQL Connection not available."

    try:
        # Check for template variables that need to be replaced
        if "{{" in query or "}}" in query:
            return False, f"Query contains template variables that need to be replaced: {query}"
        
        # Use specified_tables from Table_Names column if available
        tables_to_check = specified_tables
            
        # Clean the table names to match database conventions
        tables_to_check = [table for table in tables_to_check]
        
        # Check if query tables exist in database
        missing_tables = [table for table in tables_to_check if table not in all_db_tables]
        if missing_tables:
            return False, f"Tables not found in database: {missing_tables}"
        
        # Execute the query with retry logic for disconnection errors
        max_retries = 3 if is_us_shootings_query else 2  # More retries for us_shootings
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                cursor = connection.cursor()
                
                # For us_shootings table queries, try with smaller result sets
                if is_us_shootings_query and retry_count > 0:
                    if verbose:
                        print("Using LIMIT for us_shootings query to test connectivity...")
                    # Add a LIMIT clause for testing connectivity if not already present
                    test_query = query
                    if "LIMIT" not in test_query.upper():
                        # Strip trailing semicolon if present
                        if test_query.strip().endswith(';'):
                            test_query = test_query.strip()[:-1]
                        test_query += " LIMIT 10;"
                        
                    cursor.execute(test_query)
                    cursor.fetchall()
                    cursor.close()
                    
                    # If test query works, try full query again with a new cursor
                    cursor = connection.cursor()
                
                # Execute the query
                cursor.execute(query)
                
                # Fetch all results to clear the result set
                cursor.fetchall()
                cursor.close()
                return True, "Query executed successfully"
            except Error as e:
                error_msg = str(e)
                # Check if it's a disconnection error
                if retry_count < max_retries and (
                    "MySQL server has gone away" in error_msg or 
                    "Lost connection" in error_msg or
                    "Connection reset" in error_msg
                ):
                    # Reconnect and retry
                    retry_count += 1
                    if verbose:
                        print(f"Connection issue detected. Waiting 5 seconds before reconnecting...")
                    
                    # Wait before reconnecting, longer time
                    time.sleep(5 * retry_count)
                    
                    # Explicitly close the connection first
                    try:
                        connection.close()
                        if verbose:
                            print("Closed problematic connection.")
                    except:
                        pass  # Ignore errors when closing
                    
                    try:
                        # Create a fresh connection instead of ping
                        if conn_params:
                            connection = connect_to_mysql(**conn_params)
                        else:
                            connection = connect_to_mysql()
                            
                        if connection and connection.is_connected():
                            if verbose:
                                print(f"Created new MySQL connection, retrying query...")
                        else:
                            if verbose:
                                print("Failed to create new connection, will try again...")
                            # Wait before next attempt
                            time.sleep(2)
                            if conn_params:
                                connection = connect_to_mysql(**conn_params)
                            else:
                                connection = connect_to_mysql()
                            
                            if not connection or not connection.is_connected():
                                return False, "Failed to reconnect to MySQL after multiple attempts"
                    except Exception as conn_err:
                        if verbose:
                            print(f"Error during reconnection: {str(conn_err)}")
                        # Still try once more if we have retries left
                        if retry_count >= max_retries:
                            return False, f"Failed to reconnect: {str(conn_err)}"
                else:
                    # Not a disconnection error or max retries reached
                    # For syntax errors, provide more helpful information
                    if "1064" in error_msg:  # MySQL error code for syntax error
                        return False, f"SQL syntax error: {error_msg}"
                    return False, error_msg
    except Error as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='Test SQL queries from gold dataset on MySQL')
    parser.add_argument('--host', default='localhost', help='MySQL host')
    parser.add_argument('--user', default='root', help='MySQL user')
    parser.add_argument('--password', default='root', help='MySQL password')
    parser.add_argument('--database', default='norp_db', help='MySQL database name')
    parser.add_argument('--csv', default='dataset/gold/gold.csv', help='Path to gold CSV file')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of queries to test')
    parser.add_argument('--reconnect-interval', type=int, default=5, 
                        help='Number of queries to process before reconnecting to MySQL')
    parser.add_argument('--encoding', default='utf-8', help='CSV file encoding')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Store connection parameters for reuse
    conn_params = {
        'host': args.host,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }
    
    # Connect to MySQL
    connection = connect_to_mysql(**conn_params)
    if not connection:
        print("Failed to connect to MySQL. Exiting.")
        return
    
    print(f"Connected to MySQL database: {args.database}")
    
    # Get all tables in the database
    all_db_tables = get_all_tables(connection)
    if not all_db_tables:
        print("Failed to retrieve tables. Reconnecting and trying again...")
        if connection and connection.is_connected():
            connection.close()
        time.sleep(3)
        connection = connect_to_mysql(**conn_params)
        if not connection:
            print("Failed to reconnect to MySQL. Exiting.")
            return
        all_db_tables = get_all_tables(connection)
        if not all_db_tables:
            print("Failed to retrieve tables after reconnection. Exiting.")
            connection.close()
            return
    
    print(f"Found {len(all_db_tables)} tables in the database")
    print(f"Available tables: {', '.join(sorted(all_db_tables))}")
    
    # Read the gold CSV file
    try:
        # Try different encodings if the specified one fails
        encodings_to_try = [args.encoding, 'latin1', 'ISO-8859-1', 'utf-8-sig']
        df = None
        success_encoding = None
        
        for encoding in encodings_to_try:
            try:
                print(f"Trying to read CSV with {encoding} encoding...")
                df = pd.read_csv(args.csv, encoding=encoding)
                success_encoding = encoding
                break
            except UnicodeDecodeError:
                print(f"Failed to read with {encoding} encoding, trying next...")
            except Exception as e:
                print(f"Error reading CSV with {encoding} encoding: {e}")
        
        if df is None:
            print("Failed to read CSV with any encoding. Exiting.")
            connection.close()
            return
            
        print(f"Successfully loaded CSV with {success_encoding} encoding")
        print(f"Loaded {len(df)} queries from {args.csv}")
        
        # Check if required columns exist
        required_columns = ["SQL Query", "Table_Names"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Error: CSV is missing required columns: {missing_columns}")
            print(f"Available columns: {df.columns.tolist()}")
            connection.close()
            return
            
        # Print first few rows to verify data is loaded correctly
        if args.verbose:
            print("\nSample of loaded data:")
            pd.set_option('display.max_colwidth', 80)
            print(df[["SQL Query", "Table_Names"]].head(2).to_string())
            pd.reset_option('display.max_colwidth')
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        connection.close()
        return
    
    # Clean up queries - remove BOM markers, replace smart quotes, and other special characters
    def clean_query(query):
        if not isinstance(query, str):
            return str(query)
            
        # Remove BOM if present
        query = query.replace('\ufeff', '')
        
        # Replace smart quotes with regular quotes
        query = query.replace('"', '"').replace('"', '"')
        query = query.replace(''', "'").replace(''', "'")
        
        # Replace other problematic characters
        query = query.replace('\u2013', '-')  # en dash
        query = query.replace('\u2014', '-')  # em dash
        query = query.replace('\u2018', "'")  # left single quote
        query = query.replace('\u2019', "'")  # right single quote
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove any non-printable characters
        query = ''.join(c for c in query if c.isprintable() or c in ['\n', '\t'])
        
        # Ensure query ends with semicolon if not present
        query = query.strip()
        if not query.endswith(';'):
            query = query + ';'
            
        query = clean_column_name(query)
            
        return query
    
    # Apply cleaning to SQL Query column
    df["SQL Query"] = df["SQL Query"].apply(clean_query)
    
    # Apply limit if specified
    if args.limit:
        df = df.head(args.limit)
        print(f"Limited to testing {args.limit} queries")
    
    # Prepare results tracking
    results = []
    success_count = 0
    failure_count = 0
    
    # Track failure reasons
    failure_reasons = {}
    
    # Test each query
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Testing queries"):
        # Reconnect periodically to prevent connection timeout
        if index % args.reconnect_interval == 0 and index > 0:
            if connection and connection.is_connected():
                connection.close()
                
            # Add a sleep to help stabilize connections
            if args.verbose:
                print(f"\nPeriodic reconnection at query #{index}. Waiting 3 seconds...")
            time.sleep(3)
            
            connection = connect_to_mysql(**conn_params)
            if not connection:
                print("\nFailed to reconnect to MySQL. Stopping tests.")
                break
        
        # Verify connection is still active
        if not connection or not connection.is_connected():
            if args.verbose:
                print(f"\nConnection lost at query #{index}. Attempting to reconnect...")
            # Try to close if it exists but isn't connected
            if connection:
                try:
                    connection.close()
                except:
                    pass
            
            # Wait before reconnecting
            time.sleep(3)
            connection = connect_to_mysql(**conn_params)
            if not connection:
                print("\nFailed to reconnect to MySQL. Stopping tests.")
                break
        
        query = row["SQL Query"]
        
        # Parse table names from the Table_Names column (comma separated)
        table_names_str = str(row.get("Table_Names", ""))
        # Split by comma and clean each table name
        specified_tables = []
        for table in [t.strip() for t in table_names_str.split(",") if t.strip()]:
            # Remove any square brackets if present (common in notation like [table_name])
            table = table.strip('[]')
            specified_tables.append(table)
        
        # Test the query
        max_query_attempts = 2
        for attempt in range(max_query_attempts):
            # Verify connection before each attempt
            if not connection or not connection.is_connected():
                if args.verbose:
                    print(f"\nConnection lost before query attempt {attempt+1}. Reconnecting...")
                if connection:
                    try:
                        connection.close()
                    except:
                        pass
                connection = connect_to_mysql(**conn_params)
                if not connection:
                    print("\nFailed to reconnect to MySQL. Stopping tests.")
                    break
            
            success, message = test_query(connection, query, specified_tables, all_db_tables, 
                                         args.verbose, conn_params)
            
            # Break if successful or if the error is not connection-related
            if success or "MySQL Connection not available" not in message:
                break
            
            # Connection issue - try again after reconnecting
            if attempt < max_query_attempts - 1:
                if args.verbose:
                    print(f"\nConnection error on attempt {attempt+1}. Reconnecting...")
                if connection:
                    try:
                        connection.close()
                    except:
                        pass
                time.sleep(3 * (attempt + 1))
                connection = connect_to_mysql(**conn_params)
                if not connection:
                    print("\nFailed to reconnect to MySQL. Stopping tests.")
                    break
        
        # Update counts
        if success:
            success_count += 1
        else:
            failure_count += 1
            # Track failure reason
            if message not in failure_reasons:
                failure_reasons[message] = 0
        
        # Store the result
        results.append({
            "index": index,
            "query": query,
            "tables": specified_tables,
            "success": success,
            "message": message
        })
    
    # Close the connection
    if connection and connection.is_connected():
        connection.close()
    
    # Calculate statistics
    total_queries = len(results)
    success_rate = (success_count / total_queries) * 100 if total_queries > 0 else 0
    
    # Print results
    print(f"\nResults Summary:")
    print(f"Total queries tested: {total_queries}")
    print(f"Successful queries: {success_count}")
    print(f"Failed queries: {failure_count}")
    print(f"Success rate: {success_rate:.2f}%")
    
    # Print top failure reasons
    print("\nTop failure reasons:")
    for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        if len(reason) > 100:
            reason = reason[:97] + "..."
        print(f"  - {reason}: {count} queries")
    
    # Save detailed results to CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv("query_test_results.csv", index=False)
    print(f"\nDetailed results saved to query_test_results.csv")

if __name__ == "__main__":
    main() 