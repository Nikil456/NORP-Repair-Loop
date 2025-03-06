import os
import glob
import re
import uuid
from typing import List, Dict, Any
import sqlite3
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

class SchemaProcessor:
    def __init__(self, schema_dir: str, db_path: str, embeddings_model_name: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"):
        """
        Initialize the SchemaProcessor.
        
        Args:
            schema_dir: Directory containing the schema files
            db_path: Path to the SQLite database
            embeddings_model_name: Name of the embedding model to use (using a smaller model to save disk space)
        """
        self.schema_dir = schema_dir
        self.db_path = db_path
        self.embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
        self.conn = None
        
    def connect_to_db(self):
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
        
    def disconnect_from_db(self):
        """Disconnect from the SQLite database."""
        if self.conn:
            self.conn.close()
            
    def get_actual_tables(self) -> List[str]:
        """Get a list of actual tables in the database."""
        if not self.conn:
            self.connect_to_db()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            print(f"Found {len(table_names)} tables in the database")
            return table_names
        except sqlite3.Error as e:
            print(f"Error fetching tables: {e}")
            return []
    
    def get_column_info(self, table_name: str) -> List[Dict[str, str]]:
        """Get column information for a table."""
        if not self.conn:
            self.connect_to_db()
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            column_info = []
            for col in columns:
                column_info.append({
                    "name": col[1],
                    "type": col[2],
                    "primary_key": bool(col[5])
                })
            
            return column_info
        except sqlite3.Error as e:
            print(f"Error fetching column info for {table_name}: {e}")
            return []
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """Get foreign key relationships for a table."""
        if not self.conn:
            self.connect_to_db()
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            foreign_keys = cursor.fetchall()
            
            fk_info = []
            for fk in foreign_keys:
                fk_info.append({
                    "from_column": fk[3],
                    "to_table": fk[2],
                    "to_column": fk[4]
                })
            
            return fk_info
        except sqlite3.Error as e:
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
Columns: {columns_str}
Description: Contains data related to {table_name.replace('_', ' ').lower()}.
Relationships: {relationships_str}
"""
            
            metadata = {
                "table_name": table_name,
                "source": "database_schema"
            }
            
            return Document(page_content=content.strip(), metadata=metadata)
        except Exception as e:
            print(f"Error creating document for table {table_name}: {e}")
            return None
    
    def process_schemas(self) -> List[Document]:
        """Process all schema files and database tables to create documents."""
        self.connect_to_db()
        
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
                if table_name.lower() not in processed_tables and table_name != "sqlite_sequence":
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
    
    def create_vector_db(self, persist_directory: str = "rag/vectordb") -> Chroma:
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
                persist_directory=persist_directory,
                ids=ids
            )
            
            print(f"Created vector database with {len(documents)} documents in {persist_directory}")
            return vectordb
        except Exception as e:
            print(f"Error creating vector database: {e}")
            return None

def main():
    # Configuration
    schema_dir = "dataset/norp/schemas"
    db_path = "local_norp.db"  # Path to your SQLite database
    persist_directory = "rag/vectordb"
    
    # Create processor and vector database
    processor = SchemaProcessor(schema_dir, db_path)
    vectordb = processor.create_vector_db(persist_directory)
    
    if vectordb:
        print("Vector database created successfully!")
    else:
        print("Failed to create vector database")

if __name__ == "__main__":
    main()