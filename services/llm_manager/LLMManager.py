"""
Module to connect with LLM.
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.util import read_gpg_encrypted_file

# TODO: Make this an env variable
# Simply add the private key for LLM you are using
OPEN_AI_SENSITIVE_PATH = "sensitive/openai.txt"

class LLMManager():
    """
    Initialize OPEN AI LLM connection with file_path where key is stored.
    TO DO: Update LLM connection to the fine tuned model
    """
    def __init__(self, file_path = OPEN_AI_SENSITIVE_PATH):
        self.set_key(file_path)
        # TODO: Update connection to the fine tuned model
        # This implementation works for ChatGPT APIs
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature = 0)
        
    def set_key(self, file_path):
        self.open_ai_key = read_gpg_encrypted_file(file_path)
        os.environ["OPENAI_API_KEY"] = self.open_ai_key
    
    def invoke(self, prompt: ChatPromptTemplate, **kwargs) -> str:
        messages = prompt.format_messages(**kwargs)
        response = self.llm.invoke(messages)
        return response.content
