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
CONFIG_PATH = "config/config.json"

def read_config():
    """Read the configuration from the config file."""
    try:
        with open(CONFIG_PATH, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Config file '{CONFIG_PATH}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Config file '{CONFIG_PATH}' is not a valid JSON.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred reading config: {e}")
        return {}

class LLMManager():
    """
    Initialize OPEN AI LLM connection with API key from config.
    TO DO: Update LLM connection to the fine tuned model
    """
    def __init__(self, file_path = None):
        self.set_key(file_path)
        # TODO: Update connection to the fine tuned model
        # This implementation works for ChatGPT APIs
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature = 0)
        
    def set_key(self, file_path=None):
        if file_path:
            # Legacy method - read from encrypted file
            self.open_ai_key = read_gpg_encrypted_file(file_path)
        else:
            # New method - read from config
            config = read_config()
            self.open_ai_key = config.get("openai_api_key", "")
            
            # If key is not in config, try to read from legacy path
            if not self.open_ai_key:
                print("Warning: OpenAI API key not found in config, trying legacy path")
                try:
                    self.open_ai_key = read_gpg_encrypted_file(OPEN_AI_SENSITIVE_PATH)
                except Exception as e:
                    print(f"Error reading API key: {e}")
                    self.open_ai_key = ""
        
        # Set environment variable for OpenAI
        if self.open_ai_key:
            os.environ["OPENAI_API_KEY"] = self.open_ai_key
        else:
            print("Warning: No OpenAI API key found")
    
    def invoke(self, prompt: ChatPromptTemplate, **kwargs) -> str:
        messages = prompt.format_messages(**kwargs)
        response = self.llm.invoke(messages)
        return response.content
