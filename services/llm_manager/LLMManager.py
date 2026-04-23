"""
Module to connect with LLM.
"""
import os
import json
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.util import read_gpg_encrypted_file

# API keys are loaded from environment variables (set via .env)
class LLMManager():
    """
    Initialize LLM connection with API key (OpenAI preferred, NVIDIA fallback).
    """
    def __init__(self, config=None, file_path=None):
        """
        Initialize the LLM Manager.
        
        Args:
            config: The configuration dictionary containing API keys
            file_path: Legacy path to GPG encrypted file containing the API key
        """
        self.llm = self.initialize_llm(config, file_path)
        
    def initialize_llm(self, config=None, file_path=None):
        """ 
        Initialize LLM, preferring OpenAI over NVIDIA.
        
        Args:
            config: The configuration dictionary
            file_path: Path to GPG encrypted file
            
        Returns:
            The initialized LLM
        """
        # Try OpenAI first
        openai_key = self.get_openai_key(config, file_path)
        if openai_key:
            print("Using OpenAI API")
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.2,
                max_tokens=1024
            )
        
        # Fallback to NVIDIA
        nvidia_key = self.get_nvidia_key(config, file_path)
        if nvidia_key:
            print("Using NVIDIA API (OpenAI not available)")
            return ChatNVIDIA(
                model="meta/llama-3.3-70b-instruct",
                api_key=nvidia_key,
                temperature=0.2,
                top_p=0.7,
                max_tokens=1024
            )
        
        raise ValueError("No valid API key found for OpenAI or NVIDIA")
    
    def get_openai_key(self, config=None, file_path=None):
        """ 
        Get OpenAI API key from config or environment.
        
        Args:
            config: The configuration dictionary
            file_path: Path to GPG encrypted file
            
        Returns:
            The OpenAI API key or None
        """
        if config and "openai_api_key" in config:
            key = config.get("openai_api_key", "")
        else:
            key = os.environ.get("OPENAI_API_KEY", "")
        
        if key:
            os.environ["OPENAI_API_KEY"] = key
            print("OpenAI API key set in environment")
            return key
        return None
    
    def get_nvidia_key(self, config=None, file_path=None):
        """ 
        Get NVIDIA API key from config or environment.
        
        Args:
            config: The configuration dictionary
            file_path: Path to GPG encrypted file
            
        Returns:
            The NVIDIA API key or None
        """
        if config and "nvidia_api_key" in config:
            key = config.get("nvidia_api_key", "")
        else:
            key = os.environ.get("NVIDIA_API_KEY", "")
        
        if key:
            os.environ["NVIDIA_API_KEY"] = key
            print("NVIDIA API key set in environment")
            return key
        return None