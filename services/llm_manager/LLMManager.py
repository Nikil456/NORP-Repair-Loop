"""
Module to connect with LLM.
"""
import os
import json
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from utils.util import read_gpg_encrypted_file

# NVIDIA API key is loaded from the NVIDIA_API_KEY environment variable (set via .env)
class LLMManager():
    """
    Initialize NVIDIA LLM connection with API key.
    """
    def __init__(self, config=None, file_path=None):
        """
        Initialize the LLM Manager.
        
        Args:
            config: The configuration dictionary containing the NVIDIA API key
            file_path: Legacy path to GPG encrypted file containing the API key
        """
        api_key = self.set_key(config, file_path)
        # Initialize NVIDIA LLM with specific parameters
        self.llm = ChatNVIDIA(
            model="meta/llama-3.3-70b-instruct",
            api_key=api_key,
            temperature=0.2,
            top_p=0.7,
            max_tokens=1024
        )
        
    def set_key(self, config=None, file_path=None):
        """ 
        Set the NVIDIA API key from config or file.
        
        Args:
            config: The configuration dictionary
            file_path: Path to GPG encrypted file
            
        Returns:
            The NVIDIA API key
        """
        # First try using the config passed directly from the app
        if config and "nvidia_api_key" in config:
            self.nvidia_key = config.get("nvidia_api_key", "")
            print("Using NVIDIA API key from passed config")
        # Then try the legacy file path method
        elif file_path:
            self.nvidia_key = read_gpg_encrypted_file(file_path)
            print("Using NVIDIA API key from encrypted file")
        # Finally fall back to the environment variable
        else:
            self.nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
            print("Using NVIDIA API key from environment variable")
        
        # Set environment variable for NVIDIA
        if self.nvidia_key:
            os.environ["NVIDIA_API_KEY"] = self.nvidia_key
            print("NVIDIA API key set in environment")
        else:
            print("Warning: No NVIDIA API key found")
        
        # Return the key so it can be used directly
        return self.nvidia_key
    
    def invoke(self, prompt: ChatPromptTemplate, **kwargs) -> str:
        """
        Invoke the LLM with a prompt template and kwargs.
        
        Args:
            prompt: The prompt template to use
            kwargs: Arguments to format the prompt
            
        Returns:
            The LLM response content
        """
        messages = prompt.format_messages(**kwargs)
        response = self.llm.invoke(messages)
        return response.content