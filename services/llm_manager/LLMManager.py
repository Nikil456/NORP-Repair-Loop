"""
Module to connect with LLM.
"""
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.util import read_gpg_encrypted_file

# TODO: Make this an env variable
# Simply add the private key for LLM you are using
OPEN_AI_SENSITIVE_PATH = "sensitive/openai.txt"

class LLMManager():
    """
    Initialize OPEN AI LLM connection with API key from config.
    TO DO: Update LLM connection to the fine tuned model
    """
    def __init__(self, config=None, file_path=None):
        """
        Initialize the LLM Manager.
        
        Args:
            config: The configuration dictionary containing the OpenAI API key
            file_path: Legacy path to GPG encrypted file containing the API key
        """
        api_key = self.set_key(config, file_path)
        # TODO: Update connection to the fine tuned model
        # This implementation works for ChatGPT APIs
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=api_key)
        
    def set_key(self, config=None, file_path=None):
        """
        Set the OpenAI API key from config or file.
        
        Args:
            config: The configuration dictionary
            file_path: Path to GPG encrypted file
            
        Returns:
            The OpenAI API key
        """
        # First try using the config passed directly from the app
        if config and "openai_api_key" in config:
            self.open_ai_key = config.get("openai_api_key", "")
            print("Using OpenAI API key from passed config")
        # Then try the legacy file path method
        elif file_path:
            self.open_ai_key = read_gpg_encrypted_file(file_path)
            print("Using OpenAI API key from encrypted file")
        # Finally try reading from the default sensitive file
        else:
            try:
                self.open_ai_key = read_gpg_encrypted_file(OPEN_AI_SENSITIVE_PATH)
                print("Using OpenAI API key from default sensitive file")
            except Exception as e:
                print(f"Error reading API key: {e}")
                self.open_ai_key = ""
        
        # Set environment variable for OpenAI
        if self.open_ai_key:
            os.environ["OPENAI_API_KEY"] = self.open_ai_key
            print("OpenAI API key set in environment")
        else:
            print("Warning: No OpenAI API key found")
        
        # Return the key so it can be used directly
        return self.open_ai_key
    
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
