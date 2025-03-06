import sqlite3
import csv
import os

import mysql.connector
import pandas as pd



HOST     = '127.0.0.1'
DATABASE = 'local_norp'
USER     = 'root'
PASSWORD = 'newpassword'
# ----------------------------------------------------------------------------------------------------------------------------
# CREATE DATABASE
# ----------------------------------------------------------------------------------------------------------------------------
conn = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD
)

# Create a cursor object
cursor = conn.cursor()

# Drop the database if it exists
cursor.execute("DROP DATABASE IF EXISTS {}".format(DATABASE))
print(f"Dropped {DATABASE} database successfully.")

# Create the database
cursor.execute("CREATE DATABASE {}".format(DATABASE))
print(f"Created {DATABASE} successfully.")

# Use the database
cursor.execute("USE {}".format(DATABASE))

# Commit the changes
conn.commit()

if conn.is_connected():
    cursor.close()
    conn.close()
    print("MySQL connection is closed.")

# Connect to the database
conn = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)

# Create a cursor object
cursor = conn.cursor()
print("Connection Successful")

# Read schema files from directory and create tables
schema_dir = "dataset/schemas"
schema_files = os.listdir(schema_dir)

for schema_file in schema_files:
    if schema_file.endswith(".txt"):
        file_path = os.path.join(schema_dir, schema_file)
        with open(file_path, 'r') as f:
            schema_sql = f.read()
            cursor.execute(schema_sql)
            table_name = schema_file.replace(".txt", "")
            print(f"Created table {table_name}")

# Function to upload data from a text file
def upload_data_from_file(file_path, insert_query):
    with open(file_path, 'r') as file:
        reader = csv.reader(file, delimiter=";")

        # Insert data row by row
        for row in reader:
            cleaned_row = [
                None if field.strip() == "" else 
                1 if field.strip().lower() == "true" else 
                0 if field.strip().lower() == "false" else 
                field.strip() 
                for field in row
            ]
            cursor.execute(insert_query, cleaned_row)
    conn.commit()

# Path to the text file with data
table_data = {
    "experiencing_homelessness_age_demographics": {
        "file_path":"experiencing_homelessness_age_demographics.txt",
        "insert_query": """INSERT INTO experiencing_homelessness_age_demographics (
    	CALENDAR_YEAR, LOCATION, AGE_GROUP_PUBLIC, EXPERIENCING_HOMELESSNESS_CNT
		) VALUES (%s, %s, %s, %s);"""
	},    
    "us_shootings": {
        "file_path":"us_shootings.txt",
        "insert_query": """INSERT INTO us_shootings (
            IncidentID, Address, IncidentDate, State, CityOrCountry, VictimsKilled, VictimsInjured, 
            SuspectsInjured, SuspectsKilled, SuspectsArrested
        ) VALUES (%s, %s, (STR_TO_DATE(%s,'%M %d, %Y')), %s, %s, %s, %s, %s, %s, %s);
        """
    },
    "us_population_county": {
        "file_path":"us_population_county.txt",
        "insert_query": """INSERT INTO us_population_county (
            PopulationCount, County
        ) VALUES (%s, %s);
        """
    }, 
    "us_population": {
        "file_path":"us_population.txt",
        "insert_query": """INSERT INTO us_population (
            CensurYear, State, PopulationCount
        ) VALUES (%s, %s, %s);
        """
    }, 
    "food_access": {
        "file_path":"food_access.txt",
        "insert_query": """INSERT INTO food_access (
		CensusTract, State, County, Urban, Pop2010, Ohu2010, LILATracts_1And10, LILATracts_halfAnd10, 
		LILATracks_1And20, LILATractsVehicle, HUNVFlag, LowIncomeTracts, PovertyRate, MedianFamilyIncome, 
		LA1and10, LAhalfand10, LA1and20, LATracts_half, LATracts1, LATracts10, LATracts20, LATractsVehicle_20, 
		LAPOP1_10, LAPOP05_10, LAPOP1_20, LALOWI1_10, LALOWI05_10, LALOWI1_20, lapophalf, lalowihalf, 
		lakidshalf, laseniorshalf, lawhitehalf, lablackhalf, laasianhalf, lanhopihalf, laaianhalf, laomultirhalf, 
		lahisphalf, lahunvhalf, lasnaphalf, lapop1, lalowi1, lakids1, laseniors1, lawhite1, lablack1, laasian1, 
		lanhopi1, laaian1, laomultir1, lahisp1, lahunv1, lasnap1, lapop10, lalowi10, lakids10, laseniors10, 
		lawhite10, lablack10, laasian10, lanhopi10, laaian10, laomultir10, lahisp10, lahunv10, lasnap10, 
		lapop20, lalowi20, lakids20, laseniors20, lawhite20, lablack20, laasian20, lanhopi20, laaian20, 
		laomultir20, lahisp20, lahunv20, lasnap20, TractLOWI, TractKids, TractSeniors, TractWhite, TractBlack, 
		TractAsian, TractNHOPI, TractAIAN, TractOMultir, TractHispanic, TractHUNV, TractSNAP
	) VALUES (
		%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
		%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
		%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
		%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
	);
	""",
    },
}

for table in table_data:
    if table == "food_access": 
        continue
    else:
        upload_data_from_file(table_data[table]["file_path"], table_data[table]["insert_query"])
        print(f"Done for {table}")

# Close the database connection
conn.close()
print("Data uploaded successfully.")
