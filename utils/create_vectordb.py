import os
import glob
import re
import uuid
import argparse
import json
from typing import List, Dict, Any
import mysql.connector
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

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

class SchemaProcessor:
    def __init__(self, schema_dir: str, embeddings_model_name: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"):
        """
        Initialize the SchemaProcessor.
        
        Args:
            schema_dir: Directory containing the schema files
            embeddings_model_name: Name of the embedding model to use (using a smaller model to save disk space)
        """
        self.schema_dir = schema_dir
        self.embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
        self.config = load_config()
        self.conn = None
        
    def connect_to_db(self):
        """Connect to the MySQL database."""
        try:
            if not self.config:
                print("Failed to load configuration for database connection.")
                return False
                
            db_url = self.config["db_url"]
            self.conn = mysql.connector.connect(
                host=db_url.split('@')[1].split('/')[0],
                user=self.config["db_username"],
                password=self.config["db_password"],
                database=db_url.split('/')[-1]
            )
            print(f"Connected to MySQL database: {db_url.split('/')[-1]}")
            return True
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL database: {e}")
            return False
        
    def disconnect_from_db(self):
        """Disconnect from the MySQL database."""
        if self.conn:
            self.conn.close()
            
    def get_actual_tables(self) -> List[str]:
        """Get a list of actual tables in the database."""
        if not self.conn and not self.connect_to_db():
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            print(f"Found {len(table_names)} tables in the database")
            return table_names
        except mysql.connector.Error as e:
            print(f"Error fetching tables: {e}")
            return []
    
    def get_column_info(self, table_name: str) -> List[Dict[str, str]]:
        """Get column information for a table."""
        if not self.conn and not self.connect_to_db():
            return []
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"DESCRIBE {table_name};")
            columns = cursor.fetchall()
            
            column_info = []
            for col in columns:
                column_info.append({
                    "name": col[0],
                    "type": col[1],
                    "primary_key": col[3] == "PRI"  # MySQL DESCRIBE uses "PRI" for primary key
                })
            
            return column_info
        except mysql.connector.Error as e:
            print(f"Error fetching column info for {table_name}: {e}")
            return []
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """Get foreign key relationships for a table."""
        if not self.conn and not self.connect_to_db():
            return []
            
        try:
            cursor = self.conn.cursor()
            db_name = self.config["db_url"].split('/')[-1]
            
            # MySQL specific way to get foreign keys
            query = """
            SELECT
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE
                TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """
            cursor.execute(query, (db_name, table_name))
            foreign_keys = cursor.fetchall()
            
            fk_info = []
            for fk in foreign_keys:
                fk_info.append({
                    "from_column": fk[0],
                    "to_table": fk[1],
                    "to_column": fk[2]
                })
            
            return fk_info
        except mysql.connector.Error as e:
            print(f"Error fetching foreign keys for {table_name}: {e}")
            return []
    
    def parse_schema_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a schema file and extract relevant information."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract table name
            table_name_match = re.search(r'CREATE TABLE (\w+)', content, re.IGNORECASE)
            if not table_name_match:
                print(f"Could not extract table name from {file_path}")
                return None
            
            table_name = table_name_match.group(1)
            
            # Extract columns
            columns_text = content.split('(', 1)[1].rsplit(')', 1)[0].strip()
            column_matches = re.findall(r'(\w+)\s+([A-Za-z0-9_()]+)(?:\s+PRIMARY KEY)?', columns_text)
            
            columns = []
            for col_name, col_type in column_matches:
                if col_name.lower() not in ['foreign', 'primary', 'constraint']:
                    columns.append(f"{col_name} ({col_type})")
            
            result = {
                "table_name": table_name,
                "columns": columns,
                "file_path": file_path
            }
            
            return result
        except Exception as e:
            print(f"Error parsing schema file {file_path}: {e}")
            return None
    
    def create_table_document(self, table_name: str, schema_info=None) -> Document:
        """
        Create a document for a table with schema information.
        
        Args:
            table_name: Name of the table
            schema_info: Optional schema info from file (used if available)
            
        Returns:
            Document: A document with schema information for RAG
        """
        try:
            # Get column information from database
            column_info = self.get_column_info(table_name)
            
            # Get foreign key relationships
            fk_info = self.get_foreign_keys(table_name)
            
            # Get row count
            if self.conn:
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                cursor.close()
            else:
                row_count = "unknown"
            
            # Format columns
            columns_str = ', '.join([f"{col['name']} ({col['type']})" for col in column_info])
            
            # Format relationships
            relationships = []
            for fk in fk_info:
                relationships.append(f"{fk['from_column']} links to {fk['to_table']}.{fk['to_column']}")
            
            relationships_str = '. '.join(relationships) if relationships else "No explicit relationships defined."
            
            # Create document content
            content = f"""
Table: {table_name}
Rows: {row_count}
Columns: {columns_str}
Description: Contains data related to {table_name.replace('_', ' ').lower()}.
Relationships: {relationships_str}
"""
            
            metadata = {
                "table_name": table_name,
                "source": "database_schema",
                "row_count": row_count,
                "column_count": len(column_info)
            }
            
            return Document(page_content=content.strip(), metadata=metadata)
        except Exception as e:
            print(f"Error creating document for table {table_name}: {e}")
            return None
    
    def process_schemas(self) -> List[Document]:
        """Process all schema files and database tables to create documents."""
        if not self.connect_to_db():
            print("Failed to connect to the database")
            return []
        
        try:
            actual_tables = self.get_actual_tables()
            if not actual_tables:
                print("No tables found in the database")
                return []
                
            documents = []
            schema_files = glob.glob(os.path.join(self.schema_dir, "*.txt"))
            print(f"Found {len(schema_files)} schema files in {self.schema_dir}")
            
            # Track which tables we've processed from schema files
            processed_tables = set()
            
            # First, process schema files if they exist
            for schema_file in schema_files:
                schema_info = self.parse_schema_file(schema_file)
                if schema_info and schema_info["table_name"].lower() in [t.lower() for t in actual_tables]:
                    table_name = schema_info["table_name"]
                    document = self.create_table_document(table_name, schema_info)
                    if document:
                        documents.append(document)
                        processed_tables.add(table_name.lower())
                        print(f"Created document for table {table_name} from schema file")
            
            # Process any remaining tables from the database that weren't in schema files
            for table_name in actual_tables:
                if table_name.lower() not in processed_tables and table_name != "information_schema":
                    document = self.create_table_document(table_name)
                    if document:
                        documents.append(document)
                        print(f"Created document for table {table_name} from database")
            
            print(f"Created {len(documents)} documents in total")
            self.disconnect_from_db()
            return documents
        except Exception as e:
            print(f"Error processing schemas: {e}")
            self.disconnect_from_db()
            return []
    
    def create_vector_db(self, persist_directory: str = "data/vectordb") -> Chroma:
        """
        Create and persist a vector database from schema documents.
        
        Args:
            persist_directory: Directory to save the vector database
            
        Returns:
            Chroma: The created vector database
        """
        documents = self.process_schemas()
        
        if not documents:
            print("No documents to create vector database from")
            return None
        
        try:
            # Ensure the directory exists
            os.makedirs(persist_directory, exist_ok=True)
            
            # Generate IDs for documents (needed for Chroma)
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]
            
            # Create and persist the vector database
            vectordb = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                ids=ids,
                persist_directory=persist_directory
            )
            
            # Persist the database to disk
            vectordb.persist()
            
            return vectordb
        except Exception as e:
            print(f"Error creating vector database: {e}")
            return None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create vector database from table schemas.')
    parser.add_argument('--schema-dir', type=str, default="dataset/norp/schemas",
                      help='Directory containing schema files')
    parser.add_argument('--persist-dir', type=str, default="data/vectordb",
                      help='Directory to persist the vector database')
    parser.add_argument('--force', action='store_true',
                      help='Force recreation of the vector database')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose output')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Configuration
    schema_dir = args.schema_dir
    persist_directory = args.persist_dir
    verbose = args.verbose
    
    if verbose:
        print(f"\n=== VECTOR DATABASE CREATION PARAMETERS ===")
        print(f"Schema directory: {schema_dir}")
        print(f"MySQL database: {load_config()['db_url'].split('/')[-1] if load_config() else 'Config not loaded'}")
        print(f"Vector DB directory: {persist_directory}")
        print(f"Force recreation: {args.force}")
    
    # Check if vector DB exists and handle force flag
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        if args.force:
            if verbose:
                print(f"Existing vector database found at {persist_directory}. Forcing recreation...")
        else:
            print(f"Vector database already exists at {persist_directory}. Use --force to recreate.")
            return
    
    # Create processor and vector database
    processor = SchemaProcessor(schema_dir)
    if verbose:
        print("\nConnecting to database and processing schemas...")
    
    vectordb = processor.create_vector_db(persist_directory)
    
    if vectordb:
        if verbose:
            print("\n=== VECTOR DATABASE CREATION DETAILS ===")
            print(f"Location: {persist_directory}")
            print(f"Embedding model: {processor.embeddings.model_name}")
            print(f"Number of documents: {len(processor.process_schemas())}")
        print("Vector database created successfully!")
    else:
        print("Failed to create vector database")

if __name__ == "__main__":
    main()