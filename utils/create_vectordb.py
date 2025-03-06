import os
import chromadb
import re
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

# Define paths
SCHEMA_DIR = "dataset/schemas"
CHROMA_DB_PATH = "rag/vector_database/chroma_db"

def extract_table_info(schema_content):
    """Extract table name, columns, and relationships from schema content."""
    # Extract table name
    table_name_match = re.search(r'CREATE TABLE (\w+)', schema_content)
    if not table_name_match:
        return None
    
    table_name = table_name_match.group(1)
    
    # Extract columns with types
    column_pattern = r'^\s+(\w+)\s+([\w()]+)(?:,|$)'
    columns = []
    for line in schema_content.split('\n'):
        match = re.search(column_pattern, line)
        if match:
            column_name = match.group(1)
            column_type = match.group(2)
            columns.append((column_name, column_type))
    
    # Attempt to infer relationships (based on column names with _id suffix or common prefixes)
    relationships = []
    for column_name, _ in columns:
        if column_name.lower().endswith('_id') and column_name.lower() != 'id':
            # Infer related table from column name (e.g., customer_id → Customers)
            related_table = column_name[:-3].capitalize()
            relationships.append(f"{column_name} links to {related_table} table")
    
    return {
        "table_name": table_name,
        "columns": columns,
        "relationships": relationships
    }

def create_table_document(table_info):
    """Create a document for vectorization from table info."""
    if not table_info:
        return None
    
    # Format column information
    columns_text = ", ".join([f"{name} ({type_})" for name, type_ in table_info["columns"]])
    
    # Format relationships
    relationships_text = "Relationships: " + ", ".join(table_info["relationships"]) if table_info["relationships"] else "No explicit relationships defined."
    
    # Add description based on table name and columns (basic inference)
    description = f"Contains data related to {table_info['table_name'].replace('_', ' ').lower()}."
    
    # Construct the document
    document = f"""
Table: {table_info['table_name']}
Columns: {columns_text}
Description: {description}
{relationships_text}
    """.strip()
    
    return document

def create_vectordb():
    """Create ChromaDB with documents for each table schema."""
    print("Creating vector database for schema information...")
    
    # Create directory if not exists
    os.makedirs(os.path.dirname(CHROMA_DB_PATH), exist_ok=True)
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Use SentenceTransformer for embeddings
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Create or get collection
    collection = client.get_or_create_collection(
        name="schema_info", 
        embedding_function=sentence_transformer_ef,
        metadata={"description": "Database schema information collection"}
    )
    
    # Process schema files
    schema_files = [f for f in os.listdir(SCHEMA_DIR) if f.endswith('.txt')]
    
    documents = []
    metadatas = []
    ids = []
    
    for schema_file in schema_files:
        file_path = os.path.join(SCHEMA_DIR, schema_file)
        
        with open(file_path, 'r') as f:
            schema_content = f.read()
            
            # Extract table information
            table_info = extract_table_info(schema_content)
            
            if table_info:
                # Create document
                document = create_table_document(table_info)
                
                if document:
                    documents.append(document)
                    metadatas.append({"source": schema_file, "table_name": table_info["table_name"]})
                    ids.append(f"schema_{table_info['table_name']}")
    
    # Add documents to collection
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Added {len(documents)} schema documents to ChromaDB")
    else:
        print("No schema documents were created")

if __name__ == "__main__":
    create_vectordb()
