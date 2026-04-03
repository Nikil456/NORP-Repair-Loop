from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
import os

class SchemaRAG:
    """
    SchemaRAG: A Retrieval-Augmented Generation system for database schema context.
    This class handles retrieving relevant database schema information based on user queries
    and augmenting the prompt with this information for more accurate SQL generation.
    """
    def __init__(self, persist_directory: str = "rag/vectordb", 
                 embeddings_model_name: str = "sentence-transformers/paraphrase-MiniLM-L3-v2",
                 top_k: int = 3):
        """
        Initialize the SchemaRAG system.
        
        Args:
            persist_directory: Directory where the vector database is stored
            embeddings_model_name: Name of the embedding model to use (using smaller model to save disk space)
            top_k: Number of most relevant schema documents to retrieve
        """
        self.persist_directory = persist_directory
        self.embeddings_model_name = embeddings_model_name
        self.top_k = top_k
        self.vectordb = None
        self.embeddings = None
        
        # Try to initialize embeddings and vector database
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
            if os.path.exists(persist_directory):
                self.vectordb = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
                print(f"Successfully connected to vector database at {persist_directory}")
            else:
                print(f"Vector database not found at {persist_directory}")
        except Exception as e:
            print(f"Failed to initialize SchemaRAG: {e}")
    
    def is_initialized(self) -> bool:
        """
        Check if the RAG system is properly initialized with a vector database.
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self.vectordb is not None
        
    def retrieve_relevant_schemas(self, query: str) -> List[Document]:
        """
        Retrieve schema documents relevant to the user query.
        
        Args:
            query: User's natural language query
            
        Returns:
            List[Document]: List of relevant schema documents
        """
        if not self.is_initialized():
            print("Vector database not initialized, cannot retrieve schemas")
            return []
            
        try:
            # Perform similarity search to get relevant documents
            documents = self.vectordb.similarity_search(query, k=self.top_k)
            print(f"Retrieved {len(documents)} relevant documents for query: {query[:50]}...")
            return documents
        except Exception as e:
            print(f"Error retrieving relevant schemas: {e}")
            return []
    
    def format_schema_context(self, documents: List[Document]) -> str:
        """
        Format retrieved schema documents into a context string.
        
        Args:
            documents: List of retrieved schema documents
            
        Returns:
            str: Formatted schema context
        """
        if not documents:
            return "No schema information available."
        
        context = "Database Schema Information:\n"
        for i, doc in enumerate(documents):
            context += f"--- Schema {i+1} ---\n{doc.page_content}\n\n"
        
        return context.strip()
    
    def augment_prompt(self, query: str, base_prompt_template: ChatPromptTemplate) -> ChatPromptTemplate:
        """
        Augment the base prompt template with schema context.
        
        Args:
            query: User's natural language query
            base_prompt_template: Base prompt template to augment
            
        Returns:
            ChatPromptTemplate: Augmented prompt template
        """
        # Retrieve relevant schema documents
        documents = self.retrieve_relevant_schemas(query)
        
        # Format the schema context
        schema_context = self.format_schema_context(documents)
        
        try:
            # Create a new list of messages for the augmented template
            new_messages = []
            
            # Get the original messages
            original_messages = base_prompt_template.messages
            
            # Find the system message and augment it
            system_message_found = False
            for message in original_messages:
                if hasattr(message, 'role') and message.role == 'system':
                    # This is a system message, augment it
                    system_prompt = message.prompt.template
                    augmented_system_prompt = f"{system_prompt}\n\nRelevant Database Schema:\n{schema_context}"
                    
                    # Create a new system message with the augmented content
                    from langchain.prompts.chat import SystemMessagePromptTemplate
                    new_message = SystemMessagePromptTemplate.from_template(augmented_system_prompt)
                    new_messages.append(new_message)
                    system_message_found = True
                else:
                    # Keep other messages as they are
                    new_messages.append(message)
            
            # If no system message was found, add one
            if not system_message_found:
                print("No system message found in base prompt, adding one with schema context")
                from langchain.prompts.chat import SystemMessagePromptTemplate
                new_message = SystemMessagePromptTemplate.from_template(f"You are a SQL expert. Consider the following database schema:\n\n{schema_context}")
                new_messages.insert(0, new_message)
            
            # Create a new prompt template with the augmented messages
            augmented_template = ChatPromptTemplate.from_messages(new_messages)
            
            return augmented_template
        except Exception as e:
            print(f"Error augmenting prompt: {e}")
            return base_prompt_template  # Return the original prompt if there's an error
    
    def get_tables_from_documents(self, documents: List[Document]) -> List[str]:
        """
        Extract table names from retrieved documents.
        
        Args:
            documents: List of retrieved schema documents
            
        Returns:
            List[str]: List of table names
        """
        tables = []
        for doc in documents:
            # Extract table name from the document
            try:
                for line in doc.page_content.split('\n'):
                    if line.startswith('Table:'):
                        table_name = line.replace('Table:', '').strip()
                        tables.append(table_name)
                        break
            except Exception as e:
                print(f"Error extracting table name from document: {e}")
        
        return tables
    
    def get_relevant_tables(self, query: str) -> List[str]:
        """
        Get names of tables relevant to the query.
        
        Args:
            query: User's natural language query
            
        Returns:
            List[str]: List of relevant table names
        """
        documents = self.retrieve_relevant_schemas(query)
        return self.get_tables_from_documents(documents)
    
    def get_table_info_for_rag(self, query: str) -> str:
        """
        Get formatted table information for the query to be used in the prompt.
        This method is specifically used by app.py's run_sql_chain function.
        
        Args:
            query: User's natural language query
            
        Returns:
            str: Formatted table schema information
        """
        if not self.is_initialized():
            print("Vector database not initialized, cannot get table info")
            return ""
            
        # Get relevant documents
        documents = self.retrieve_relevant_schemas(query)
        
        if not documents:
            print("No relevant documents found for query")
            return ""
            
        try:
            # Extract and format table information
            table_info = []
            print(f"rag documents: {documents}")
            for doc in documents:
                table_info.append(doc.page_content)
            print(f"inside rag table_info: {table_info}")
            return "\n\n".join(table_info)
        except Exception as e:
            print(f"Error formatting table info: {e}")
            return ""
    
    def process_query(self, query: str, base_prompt_template: ChatPromptTemplate) -> Dict[str, Any]:
        """
        Process a user query and return augmented prompt and relevant information.
        
        Args:
            query: User's natural language query
            base_prompt_template: Base prompt template
            
        Returns:
            Dict: Dictionary containing augmented prompt and relevant tables
        """
        # Retrieve relevant schema documents
        documents = self.retrieve_relevant_schemas(query)
        
        # Format schema context
        schema_context = self.format_schema_context(documents)
        
        # Get relevant table names
        relevant_tables = self.get_tables_from_documents(documents)
        
        # Augment the prompt
        augmented_prompt = self.augment_prompt(query, base_prompt_template)
        
        return {
            "augmented_prompt": augmented_prompt,
            "schema_context": schema_context,
            "relevant_tables": relevant_tables,
            "documents": documents
        }
