import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

# Constants
CHROMA_DB_PATH = "rag/vector_database/chroma_db"
DEFAULT_TOP_K = 3

class SchemaRAG:
    """Class to handle retrieval and augmentation of schema information."""
    
    def __init__(self):
        """Initialize the SchemaRAG with ChromaDB client."""
        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        self.embedding_function = None
        
        # Initialize if DB exists
        if os.path.exists(CHROMA_DB_PATH):
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            
            # Use SentenceTransformer for embeddings
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Get collection
            self.collection = self.client.get_collection(
                name="schema_info", 
                embedding_function=self.embedding_function
            )
            return True
        except Exception as e:
            print(f"Error initializing ChromaDB client: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if RAG is properly initialized."""
        return self.client is not None and self.collection is not None
    
    def retrieve_schema_info(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant schema information based on the query.
        
        Args:
            query: The user query to find relevant schema information
            top_k: Number of schema documents to retrieve
            
        Returns:
            List of schema information documents with metadata
        """
        if not self.is_initialized():
            if not self._initialize_client():
                # Failed to initialize
                return []
        
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Prepare results
            schema_info = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}
                    schema_info.append({
                        'content': doc,
                        'metadata': metadata,
                        'score': results['distances'][0][i] if 'distances' in results and results['distances'][0] else None
                    })
            
            return schema_info
        except Exception as e:
            print(f"Error retrieving schema information: {e}")
            return []
    
    def augment_prompt_with_schema(self, query: str, top_k: int = DEFAULT_TOP_K) -> str:
        """
        Augment the user query with schema information.
        
        Args:
            query: The user query
            top_k: Number of schema documents to retrieve
            
        Returns:
            Augmented prompt with schema information
        """
        schema_info = self.retrieve_schema_info(query, top_k)
        
        if not schema_info:
            return query
        
        # Format retrieved schema information
        schema_context = "\n\n".join([doc['content'] for doc in schema_info])
        
        # Create augmented prompt
        augmented_prompt = f"""
I need to generate a SQL query for the following question: "{query}"

Here is the relevant database schema information:

{schema_context}

Based on this schema information, generate a correct SQL query.
""".strip()
        
        return augmented_prompt
    
    def get_table_info_for_rag(self, query: str, top_k: int = DEFAULT_TOP_K) -> str:
        """
        Get formatted table info for RAG pipeline (compatible with existing app).
        
        Args:
            query: The user query
            top_k: Number of schema documents to retrieve
            
        Returns:
            Formatted table info for the LLM
        """
        schema_info = self.retrieve_schema_info(query, top_k)
        
        if not schema_info:
            return ""
        
        # Format retrieved schema information as table info
        table_info_sections = []
        
        for doc in schema_info:
            # Parse the document content
            content = doc['content']
            table_info_sections.append(content)
        
        # Join all tables information
        return "\n\n".join(table_info_sections)
