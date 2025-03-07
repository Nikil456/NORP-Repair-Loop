import mysql.connector
from mysql.connector import Error
import argparse

def connect_to_mysql(host="localhost", user="root", password="root", database="norp_db"):
    """Establishes connection to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connection_timeout=60
        )
        if connection.is_connected():
            print(f"Connected to MySQL database: {database}")
            return connection
        else:
            print("Failed to connect to MySQL database")
            return None
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def run_query(connection, query, show_results=True, limit_results=5):
    """Run a query and optionally show results"""
    try:
        cursor = connection.cursor(dictionary=True)
        print(f"\nExecuting query:\n{query}")
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if show_results:
            result_count = len(results)
            print(f"\nQuery results (showing {min(limit_results, result_count)} of {result_count} rows):")
            for i, row in enumerate(results):
                if i < limit_results:
                    print(row)
                else:
                    break
        
        cursor.close()
        print("\nQuery executed successfully!")
        return True
    except Error as e:
        print(f"\nQuery error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test a single MySQL query")
    parser.add_argument("--host", default="localhost", help="MySQL host")
    parser.add_argument("--user", default="root", help="MySQL user")
    parser.add_argument("--password", default="root", help="MySQL password")
    parser.add_argument("--database", default="norp_db", help="MySQL database")
    args = parser.parse_args()
    
    # Connect to database
    connection = connect_to_mysql(args.host, args.user, args.password, args.database)
    if not connection:
        return
    
    # The problematic query
    query = """
    SELECT 
        STR_TO_DATE(CONCAT(DATE_FORMAT(IncidentDate, '%Y-%m'), '-01'), '%Y-%m-%d') AS IncidentDate,
        COUNT(*) AS count
    FROM us_shootings
    GROUP BY STR_TO_DATE(CONCAT(DATE_FORMAT(IncidentDate, '%Y-%m'), '-01'), '%Y-%m-%d')
    ORDER BY STR_TO_DATE(CONCAT(DATE_FORMAT(IncidentDate, '%Y-%m'), '-01'), '%Y-%m-%d') ASC
    """
    
    # Run the query
    run_query(connection, query)
    
    # Close connection
    connection.close()
    print("\nConnection closed.")

if __name__ == "__main__":
    main() 