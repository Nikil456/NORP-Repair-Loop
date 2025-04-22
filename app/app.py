import os
import sys
import asyncio

# Add the parent directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from services.service_manager import ServiceManager
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.base import Chain
import gnupg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import json
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables.base import RunnableLambda
from utils.constants import *
from config.prompts import *
from auto_correction.auto_correction import AutoCorrection
from fastapi.concurrency import run_in_threadpool

# Import RAG if available
try:
    from rag.rag import SchemaRAG
    rag_available = True
except ImportError:
    rag_available = False

# GPG_BINARY_PATH = "/opt/homebrew/bin/gpg"
SENSITIVE_PATH = "sensitive/openai.txt"

# gpg = gnupg.GPG(binary=GPG_BINARY_PATH)
def read_json(file_name):
    try:
        # Try to open the file from the current directory first
        try:
            with open(file_name, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            # If not found, try from the config directory
            config_path = os.path.join('config', file_name)
            with open(config_path, 'r') as file:
                data = json.load(file)
                return data
    except FileNotFoundError:
        print(f"Error: File '{file_name}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: File '{file_name}' is not a valid JSON.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Example usage
config_details = read_json('config.json')
if config_details is None:
    print("Failed to load configuration. Using default values.")
    config_details = {
        "db_url": "sqlite:///local_norp.db",
        "db_username": "",
        "db_password": "",
        "redis_host_url": "localhost",
        "redis_port": "6379",
        "redis_password": None,
        "openai_api_key": "REDACTED"
    }

app = FastAPI()

# Initialize the service manager
service_manager = ServiceManager(config_details)
redis_client = service_manager.get_redis()
redis_client = redis_client.redis
db = service_manager.get_db()
llm = service_manager.get_llm()

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


class ChatMessage(BaseModel):
    session_id: str
    message: str
    message_type: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    sql_query: Optional[str]
    query_result: Optional[str]
    history: List[dict]

async def run_sql_chain(question: str, history: List[dict], session_id: str, memory: ConversationBufferMemory, use_rag: bool = False):
    """Run the SQL generation chain with conversation history"""
    
    # Get table information - use RAG if enabled and available
    if use_rag and rag_available:
        # Initialize SchemaRAG
        schema_rag = SchemaRAG()
        
        # Get relevant table info using RAG
        if schema_rag.is_initialized():
            table_info = schema_rag.get_table_info_for_rag(question)
            print(f"RAG table_info: {table_info}")
            assert table_info is not None, "RAG table_info is None"
            if not table_info:  # Fallback to complete table info if RAG returns nothing
                table_info = db.get_table_info()
            # Log RAG table info
            try:
                with open("rag_table_info.txt", "a") as f:
                    f.write(f"{table_info}\n{'-'*80}\n")
            except FileNotFoundError:
                with open("rag_table_info.txt", "w") as f:
                    f.write(f"{table_info}\n{'-'*80}\n")
        else:
            # Fallback to regular table_info if RAG not initialized
            table_info = db.get_table_info()
            # Log non-RAG table info when RAG fails
            try:
                with open("non_rag_table_info.txt", "a") as f:
                    f.write(f"{table_info}\n{'-'*80}\n")
            except FileNotFoundError:
                with open("non_rag_table_info.txt", "w") as f:
                    f.write(f"{table_info}\n{'-'*80}\n")
    else:
        # Use regular table info
        table_info = db.get_table_info()
        # Log non-RAG table info
        try:
            with open("non_rag_table_info.txt", "a") as f:
                f.write(f"{table_info}\n{'-'*80}\n")
        except FileNotFoundError:
            with open("non_rag_table_info.txt", "w") as f:
                f.write(f"{table_info}\n{'-'*80}\n")
 
    # Prepare messages for the prompt
    messages = []
    
    if not history:
        print(f"wihout table_info: {table_info}")
        # For initial prompt (no history)
        initial_prompt_value = INITIAL_PROMPT.invoke({
            "table_info": table_info,
            "top_k": TOP_K_ROWS  
        })
        continuation_prompt_value = CONTINUATION_PROMPT.invoke({
            "question": f"Here is the table info ONLY use table names specified after Table: and column names specified after Column: in your SQL query: {table_info}\n\n{question}",
            "history": []
        })
        messages.extend(initial_prompt_value.messages)
        messages.extend(continuation_prompt_value.messages)
    else:
        print(f"with table_info: {table_info}")
        # For continuation prompt (with history)˜†
        continuation_prompt_value = CONTINUATION_PROMPT.invoke({
            "question": f"Here is the table info ONLY use table names specified after Table: and column names specified after Column: in your SQL query: {table_info}\n\n{question}",
            "history": history
        })
        messages.extend(continuation_prompt_value.messages)
    print(f"messages: {messages}")
    # Ensure all messages are of type BaseMessage with correct types
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            msg_type = msg.get("type", "human")  # Default to "human" if type is missing
            content = msg.get("content", "")

            if msg_type == "system":
                formatted_messages.append(SystemMessage(content=content))
            elif msg_type == "human":
                formatted_messages.append(HumanMessage(content=content))
        elif isinstance(msg, BaseMessage):
            # If already a BaseMessage, add directly
            formatted_messages.append(msg)
        else:
            raise ValueError(f"Unexpected message format: {msg}")

    # Create the SQL generation chain
    print(f"Creating chain")
    sql_generation_chain = (
        RunnableLambda(lambda x: x)  # Pass messages directly
        | llm
    )
    print(f"Invoking chain")

    max_retries = 5
    timeout_seconds = 25
    result = None
    last_exception = None

    for attempt in range(max_retries):
        try:
            print(f"Attempting chain invocation (Attempt {attempt + 1}/{max_retries})...")
            # Invoke the chain with timeout
            result = await asyncio.wait_for(
                sql_generation_chain.ainvoke(formatted_messages),
                timeout=timeout_seconds
            )
            print(f"Chain invocation successful (Attempt {attempt + 1}).")
            print(f"SQL Generation LLM call completed. Result content: {result.content[:100]}...") # Log completion
            break  # Exit loop if successful
        except asyncio.TimeoutError:
            print(f"Chain invocation timed out after {timeout_seconds} seconds (Attempt {attempt + 1}/{max_retries}). Retrying...")
            last_exception = asyncio.TimeoutError(f"Chain invocation failed after {max_retries} attempts due to timeout.")
            # Optional: await asyncio.sleep(1) # Add a small delay before retrying if desired
        except Exception as e:
            print(f"Chain invocation failed with non-timeout error on attempt {attempt + 1}: {e}")
            last_exception = e
            break # Break on non-timeout errors

    if result is None:
        # If all retries failed, raise the last known exception
        if last_exception:
            # Ensure the exception is raiseable, wrap if necessary
            if isinstance(last_exception, BaseException):
                 raise last_exception
            else:
                 raise Exception(f"Chain invocation failed after retries: {last_exception}")
        else:
            # Fallback if loop didn't even run once or break correctly
            raise Exception("Chain invocation failed after multiple retries for an unknown reason.")

    # update redis and history
    for msg in messages:
        # Check message type
        message_type = ""
        message = ""
        if isinstance(msg, SystemMessage):
            message_type="system"
            message = msg.content
        elif isinstance(msg, HumanMessage):
            message_type="human"
            message = msg.content
        elif isinstance(msg, AIMessage):
            message_type="ai"
            message = msg.content
        elif isinstance(msg, MessagesPlaceholder):
            continue
        if message_type and message:
           update_chat_memory_and_redis_history(session_id, message, 
                                                message_type, memory)

    memory = update_chat_memory_and_redis_history(session_id, result.content, 
                                                  "ai", memory)
    print(f"Returning result and memory")
    return (result, memory)
    

# Define the request body model using Pydantic
class ChatRequest(BaseModel):
    session_id: Union[int, str]
    message: str
    message_type: str
    use_rag: bool = False  # Optional flag to enable RAG
    use_auto_correction: bool = False  # Optional flag to enable auto-correction, defaults to True
    generate_summary: bool = True  # Optional flag to enable natural language summary generation

class ChatResponse(BaseModel):
    session_id: str
    response: str
    sql_query: Optional[str]
    sql_valid: bool
    query_result: Optional[str]

def get_message_history(session_id: Union[int, str]) -> ConversationBufferMemory:
    """Get message history from Redis cache or create a new memory object"""
    try:
        # Convert the session_id to string to ensure consistent key format
        session_id_str = str(session_id)
        
        # Check if we have a cache for this session ID
        cached_messages = redis_client.lrange(f"chat:{session_id_str}", 0, -1)
        print(f"length of cached essages  {len(cached_messages)}")
        
        # Create a new ConversationBufferMemory
        memory = ConversationBufferMemory(
            memory_key="history",
            return_messages=True,
        )

        # If we have cached messages, add them to the memory
        if cached_messages:
            for message_json in cached_messages:
                try:
                    message = json.loads(message_json)
                    if message["type"] == "human":
                        memory.chat_memory.add_message(HumanMessage(content=message["content"]))
                    elif message["type"] == "ai":
                        memory.chat_memory.add_message(AIMessage(content=message["content"]))
                    elif message["type"] == "system":
                        memory.chat_memory.add_message(SystemMessage(content=message["content"]))
                except Exception as e:
                    print(f"Error parsing cached message: {e}")
                    continue
        
        return memory
    except Exception as e:
        print(f"Error getting message history: {e}")
        # Return a new memory object in case of error
        return ConversationBufferMemory(memory_key="history", return_messages=True)


def update_chat_memory_and_redis_history(session_id: Union[int, str], message_content:str, message_type:str, 
                                         memory: ConversationBufferMemory) -> ConversationBufferMemory:
    """Save updated chat history to Redis cache and memory object"""
    try:
        # Convert the session_id to string to ensure consistent key format
        session_id_str = str(session_id)
        
        # Update cache
        message = {
            "type": message_type,
            "content": message_content
        }
        # Convert the message to a JSON string
        message_json = json.dumps(message)
        # Append the message to the list associated with the session ID
        # rpush takes care if the session_id does not exist
        redis_client.rpush(f"chat:{session_id_str}", message_json)
        # Update the TTL for the session ID
        redis_client.expire(f"chat:{session_id_str}", CHAT_HISTORY_TTL)
        print(f"Message appended to session {session_id_str} and TTL updated to {CHAT_HISTORY_TTL} seconds")

        # Update conversation buffer memory
        if message_type == 'human':
            memory.chat_memory.add_message(HumanMessage(content=message_content))
        elif message_type == 'ai':
            memory.chat_memory.add_message(AIMessage(content=message_content))
        elif message_type == 'system':
            memory.chat_memory.add_message(SystemMessage(content=message_content))
        
        return memory
    except Exception as e:
        print(f"Error updating chat memory: {e}")
        return memory

async def execute_sql_query(sql_query:str):
    execute_query = QuerySQLDataBaseTool(db=db)
    query_results=None
    try:
        # Run the synchronous database tool in a thread pool
        query_results = await run_in_threadpool(execute_query.invoke, {"query": sql_query})
    except Exception as e:
        # TODO: Add feedback loop here when memory issue is sorted
        error_message = str(e)
        print(error_message)
    return query_results

# Define the POST request handler for sending the prompt
# remove chat response
# @app.post("/query", response_model=ChatResponse)
@app.post("/query")
async def handle_query(request: Request):
    json_data = await request.json()
    chat_request = ChatRequest(
        session_id=json_data["session_id"],
        message=json_data["question"],
        message_type=json_data["message_type"],
        use_rag=json_data.get("use_rag", False),
        use_auto_correction=json_data.get("use_auto_correction", True),
        generate_summary=json_data.get("generate_summary", True)
    )
    
    if not chat_request.message:
        raise HTTPException(status_code=400, detail="No question provided")
    
    sql_query = None
    query_results = None 
    memory = get_message_history(chat_request.session_id)
    natural_language_summary = "Could not generate summary." # Default value
    
    # Initialize auto-correction if enabled
    auto_correction = AutoCorrection(llm, execute_sql_query) if chat_request.use_auto_correction else None
    
    # Invoke the chain with the question
    print("Attempting to generate initial SQL...")
    try:
        sql_query_response, memory = await run_sql_chain(
            chat_request.message,
            memory.load_memory_variables({})["history"],
            chat_request.session_id,
            memory,
            chat_request.use_rag
        )
    except Exception as e:
        print(f"Error during initial SQL generation: {e}")
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    
    print("Initial SQL generated successfully.")
    # Extract the raw SQL query string
    content = sql_query_response.content
    if content.startswith('```sql') and content.endswith('```'):
        initial_sql_query = content[6:-3].strip()
    else:
        initial_sql_query = content.strip()

    final_sql_query = initial_sql_query # Default to initial query
    
    try:
        if chat_request.use_auto_correction and auto_correction:
            print("Attempting auto-correction...")
            # Try to execute the query with auto-correction
            corrected_query, correction_explanation, correction_metadata = await auto_correction.correct_query(
                initial_sql_query,
                "",  # No initial error message
                chat_request.message
            )
            final_sql_query = corrected_query # Update final query if corrected
            print(f"Auto-correction completed. Corrected query: {final_sql_query}")
            
            # Execute the final query
            print("Executing final (corrected) SQL query...")
            query_results = await execute_sql_query(final_sql_query)
            print("Final (corrected) SQL query executed.")
            
            # Generate summary for the corrected query if enabled
            if chat_request.generate_summary:
                try:
                    summary_messages = SQL_SUMMARY_TEMPLATE.format_messages(
                        user_question=chat_request.message,
                        sql_query=final_sql_query
                    )
                    summary_response = await llm.ainvoke(summary_messages)
                    natural_language_summary = summary_response.content
                    print("Generated summary for corrected query.")
                except Exception as summary_error:
                    print(f"Error generating summary: {summary_error}")

            # Update the response with correction information and summary
            return {
                "sql_query": final_sql_query,
                "query_results": query_results,
                "natural_language_summary": natural_language_summary if chat_request.generate_summary else None,
                "correction_explanation": correction_explanation,
                "correction_metadata": correction_metadata,
                "auto_correction_used": True
            }
        else:
            # Execute query without auto-correction
            final_sql_query = initial_sql_query # Final query is the initial one
            print("Executing initial SQL query (no auto-correction)...")
            query_results = await execute_sql_query(final_sql_query)
            print("Initial SQL query executed (no auto-correction).")

            # Generate summary for the initial query if enabled
            if chat_request.generate_summary:
                try:
                    summary_messages = SQL_SUMMARY_TEMPLATE.format_messages(
                        user_question=chat_request.message,
                        sql_query=final_sql_query
                    )
                    summary_response = await llm.ainvoke(summary_messages)
                    natural_language_summary = summary_response.content
                    print("Generated summary for initial query.")
                except Exception as summary_error:
                    print(f"Error generating summary: {summary_error}")
                
            return {
                "sql_query": final_sql_query,
                "query_results": query_results,
                "natural_language_summary": natural_language_summary if chat_request.generate_summary else None,
                "auto_correction_used": False
            }
            
    except Exception as e:
        print(f"Error executing query or generating summary: {e}")
        # Attempt to return basic info even if execution/summary fails
        print(f"Returning response")
        return {
             "sql_query": final_sql_query,
             "query_results": f"Error during execution or summary generation: {str(e)}",
             "natural_language_summary": "Could not generate summary due to error." if chat_request.generate_summary else None,
             "auto_correction_used": chat_request.use_auto_correction
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
