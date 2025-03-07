import mysql.connector
from mysql.connector import Error
import sys

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

def check_table_structure(connection, table_name):
    """Check the structure of a table"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        print(f"\nStructure of {table_name} table:")
        for column in columns:
            print(f"  {column[0]}: {column[1]}")
        cursor.close()
    except Error as e:
        print(f"Error checking table structure: {e}")

def sample_data(connection, table_name, limit=5):
    """Get sample data from a table"""
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cursor.fetchall()
        print(f"\nSample data from {table_name} (first {limit} rows):")
        for row in rows:
            print(row)
        cursor.close()
    except Error as e:
        print(f"Error getting sample data: {e}")

def test_problematic_query(connection):
    """Test the specific problematic query"""
    query = """
    SELECT STR_TO_DATE(CONCAT(DATE_FORMAT(`us_shootings`.`IncidentDate`, '%Y-%m'), '-01'), '%Y-%m-%d') AS `IncidentDate`,
           COUNT(*) AS `count`
    FROM `us_shootings`
    GROUP BY STR_TO_DATE(CONCAT(DATE_FORMAT(`us_shootings`.`IncidentDate`, '%Y-%m'), '-01'), '%Y-%m-%d')
    ORDER BY STR_TO_DATE(CONCAT(DATE_FORMAT(`us_shootings`.`IncidentDate`, '%Y-%m'), '-01'), '%Y-%m-%d') ASC
    """
    try:
        print("\nTesting problematic query:")
        print(query)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"\nQuery results (count: {len(rows)}):")
        for i, row in enumerate(rows):
            if i < 5:  # Show only first 5 rows
                print(row)
            else:
                print("...")
                break
        cursor.close()
        print("\nQuery executed successfully!")
    except Error as e:
        print(f"\nQuery error: {e}")

def check_incident_date_format(connection):
    """Check the format of the IncidentDate column"""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT IncidentDate FROM us_shootings LIMIT 10")
        dates = cursor.fetchall()
        print("\nSample IncidentDate values:")
        for date in dates:
            print(f"  {date[0]} (type: {type(date[0])})")
        cursor.close()
    except Error as e:
        print(f"Error checking date format: {e}")

def main():
    # Connect to the database
    connection = connect_to_mysql()
    if not connection:
        sys.exit(1)
    
    # Check the us_shootings table
    table_name = "us_shootings"
    check_table_structure(connection, table_name)
    sample_data(connection, table_name)
    check_incident_date_format(connection)
    
    # Test the problematic query
    test_problematic_query(connection)
    
    # Close the connection
    connection.close()
    print("\nConnection closed.")

if __name__ == "__main__":
    main() 