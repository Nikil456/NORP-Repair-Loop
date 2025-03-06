import unittest
from unittest.mock import patch, MagicMock
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from services.llm_manager.LLMManager import LLMManager

class TestLLMManager(unittest.TestCase):
    @patch("app.LLMManager.read_gpg_encrypted_file")
    @patch("os.environ")
    @patch("langchain_openai.ChatOpenAI")
    def test_llm_manager(self, mock_chat_openai, mock_environ, mock_read_file):
        # Mock the output of read_gpg_encrypted_file
        mock_read_file.return_value = "mock_openai_key"

        # Mock ChatOpenAI behavior
        mock_llm_instance = MagicMock()
        mock_chat_openai.return_value = mock_llm_instance
        
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = "mock_response"
        mock_llm_instance.invoke.return_value = mock_response
        print("yay")
        # Test the LLMManager initialization
        llm_manager = LLMManager()
        print("nay")
        # mock_read_file.assert_called_once_with("sensitive/openai.txt")
        # mock_environ.__setitem__.assert_called_once_with("OPENAI_API_KEY", "mock_openai_key")
        # mock_chat_openai.assert_called_once_with(model="gpt-3.5-turbo", temperature=0)

        # Test the invoke method
        mock_prompt = MagicMock(spec=ChatPromptTemplate)
        mock_prompt.format_messages.return_value = [MagicMock(spec=BaseMessage)]
        response = llm_manager.invoke(mock_prompt, key="value")
        
        mock_prompt.format_messages.assert_called_once_with(key="value")
        mock_llm_instance.invoke.assert_called_once()
        self.assertEqual(response, "mock_response")

if __name__ == "__main__":
    unittest.main()
