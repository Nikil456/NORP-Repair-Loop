from typing import Optional, Tuple, Dict, Any
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from config.prompts import SQL_CORRECTION_TEMPLATE, SQL_SELF_CHECK_TEMPLATE
from rag.rag import SchemaRAG
import json
import re

# Constants for auto-correction
MAX_CORRECTION_ATTEMPTS = 5

class AutoCorrection:
    def __init__(self, llm: ChatOpenAI, execute_query_func):
        """
        Initialize the AutoCorrection system.
        
        Args:
            llm: The language model to use for corrections
            execute_query_func: Function to execute SQL queries
        """
        self.llm = llm
        self.execute_query_func = execute_query_func
        self.correction_template = SQL_CORRECTION_TEMPLATE
        self.self_check_template = SQL_SELF_CHECK_TEMPLATE
        self.schema_rag = SchemaRAG()
        
    def _get_relevant_schema(self, user_request: str) -> str:
        """Get relevant table schema information for the query."""
        if self.schema_rag.is_initialized():
            table_info = self.schema_rag.get_table_info_for_rag(user_request)
            if table_info:
                return table_info
        return ""  # Return empty string if RAG is not initialized or no relevant schema found
        
    def _extract_json_from_response(self, response: str) -> dict:
        """Extract JSON from the response, handling potential formatting issues."""
        try:
            # First try direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to find JSON-like content using regex
            json_pattern = r'\{[\s\S]*\}'
            match = re.search(json_pattern, response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to parse JSON from response: {response}")
            raise ValueError(f"No valid JSON found in response: {response}")
        
    def _parse_correction_response(self, response: str) -> Tuple[str, str]:
        """Parse the correction response to extract query and explanation."""
        try:
            parsed = self._extract_json_from_response(response)
            
            # Validate required fields
            if "corrected_query" not in parsed or "explanation" not in parsed:
                raise ValueError("Response missing required fields")
                
            query = parsed["corrected_query"].strip()
            explanation = parsed["explanation"].strip()
            
            # Validate the parsed response
            if not query:
                raise ValueError("No corrected query provided in the response")
                
            return query, explanation
            
        except Exception as e:
            raise ValueError(f"Failed to parse correction response: {str(e)}")
        
    def _parse_self_check_response(self, response: str) -> Dict[str, Any]:
        """Parse the self-check response."""
        try:
            parsed = self._extract_json_from_response(response)
            
            # Validate required fields
            required_fields = ["explanation", "matches_intent", "potential_issues"]
            if not all(field in parsed for field in required_fields):
                raise ValueError("Response missing required fields")
            
            # Ensure potential_issues is a list
            if not isinstance(parsed["potential_issues"], list):
                parsed["potential_issues"] = [parsed["potential_issues"]] if parsed["potential_issues"] else []
            
            # Ensure matches_intent is boolean
            if isinstance(parsed["matches_intent"], str):
                parsed["matches_intent"] = parsed["matches_intent"].lower() == "true"
            
            return {
                "explanation": parsed["explanation"].strip(),
                "matches_intent": bool(parsed["matches_intent"]),
                "potential_issues": parsed["potential_issues"]
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse self-check response: {str(e)}")
        
    async def correct_query(self, sql_query: str, error_message: str, user_request: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Attempt to correct a failed SQL query.
        
        Args:
            sql_query: The original SQL query that failed
            error_message: The error message from the failed execution
            user_request: The original user request in natural language
            
        Returns:
            Tuple containing:
            - Corrected SQL query
            - Explanation of the correction
            - Metadata about the correction process
        """
        attempts = 0
        current_query = sql_query
        correction_history = []
        error_type = "INITIAL_ERROR"
        last_error = error_message
        
        # Get relevant schema information
        table_info = self._get_relevant_schema(user_request)
        
        while attempts < MAX_CORRECTION_ATTEMPTS:
            try:
                # Try to execute the current query
                result = self.execute_query_func(current_query)
                
                # Check if result indicates any issues
                if result is None:
                    error_message = "Query returned no results. This might indicate an issue with table names, join conditions, or WHERE clauses."
                    raise ValueError(error_message)
                
                # If we get here, query executed successfully - now check the results
                if isinstance(result, str) and ("error" in result.lower() or "exception" in result.lower()):
                    # Result contains an error message
                    error_message = result
                    raise ValueError(error_message)
                
                # Query executed and returned results - perform self-check
                self_check_result = await self.self_check_query(current_query, user_request, table_info)
                
                # Even if query executes, we need to verify both intent and result quality
                if self_check_result["matches_intent"]:
                    # Additional validation of results
                    if isinstance(result, (list, dict)) and not result:
                        error_message = "Query executed but returned empty results. This might indicate overly restrictive conditions."
                        raise ValueError(error_message)
                    
                    # Success case - we have valid results and matching intent
                    return current_query, "Query executed successfully with valid results", {
                        "attempts": attempts + 1,
                        "correction_history": correction_history,
                        "self_check": self_check_result,
                        "result_sample": str(result)[:200] if result else "No results",
                        # "final_result": result,
                        "table_info_used": bool(table_info)
                    }
                else:
                    # Query executed but doesn't match intent
                    error_message = f"Query executed but may not match intent: {self_check_result['potential_issues']}"
                    raise ValueError(error_message)
                    
            except Exception as e:
                last_error = str(e)
                
                # Categorize the error for better correction guidance
                
                if "unknown column" in last_error.lower():
                    error_type = "COLUMN_ERROR"
                elif "syntax" or "syntactical" in last_error.lower():
                    error_type = "SYNTAX_ERROR"
                elif "table" in last_error.lower() and ("unknown" in last_error.lower() or "not found" in last_error.lower()):
                    error_type = "TABLE_ERROR"
                elif "group by" in last_error.lower():
                    error_type = "GROUP_BY_ERROR"
                elif "empty results" in last_error.lower():
                    error_type = "EMPTY_RESULTS"
                elif "intent" in last_error.lower():
                    error_type = "INTENT_MISMATCH"
                else:
                    error_type = "GENERAL_ERROR"
                
                # Update error message with categorization
                error_message = f"[{error_type}] {last_error}"
            
            try:
                # Prepare correction prompt with table info
                correction_messages = self.correction_template.format_messages(
                    original_query=current_query,
                    error_message=error_message,
                    user_request=user_request,
                    table_info=f"\nAvailable table schema:\n{table_info}" if table_info else ""
                )
                print("correction_messages", correction_messages)
                # Get correction from LLM
                correction_response = await self.llm.ainvoke(correction_messages)
                corrected_query, explanation = self._parse_correction_response(correction_response.content)
                
                # Validate the corrected query 
                if not corrected_query or corrected_query.isspace():
                    raise ValueError("Empty or invalid correction received")
                
                if corrected_query == current_query:
                    raise ValueError("Correction identical to current query")
                
                # Update correction history
                correction_history.append({
                    "attempt": attempts + 1,
                    "error": error_message,
                    "error_type": error_type,
                    "correction": corrected_query,
                    "explanation": explanation,
                    "table_info_used": bool(table_info)
                })
                
                # Update for next iteration
                current_query = corrected_query
                
            except Exception as correction_error:
                # If we fail to get a valid correction, add it to history and break
                correction_history.append({
                    "attempt": attempts + 1,
                    "error": error_message,
                    "error_type": error_type,
                    "correction": None,
                    "explanation": f"Failed to get valid correction: {str(correction_error)}",
                    "table_info_used": bool(table_info)
                })
                break
                
            attempts += 1
            
        # If we reach here, we've exceeded max attempts or failed to get a valid correction
        return current_query, f"Failed to correct query after {attempts} attempts", {
            "attempts": attempts,
            "correction_history": correction_history,
            "final_error": last_error,
            "error_type": error_type,
            "table_info_used": bool(table_info)
        }
        
    async def self_check_query(self, sql_query: str, user_request: str, table_info: str = "") -> Dict[str, Any]:
        """
        Perform self-check on a SQL query to verify it matches user intent.
        
        Args:
            sql_query: The SQL query to check
            user_request: The original user request in natural language
            table_info: Optional table schema information
            
        Returns:
            Dictionary containing the self-check results
        """
        check_messages = self.self_check_template.format_messages(
            sql_query=sql_query,
            user_request=user_request,
            table_info=f"\nAvailable table schema:\n{table_info}" if table_info else ""
        )
        
        check_response = await self.llm.ainvoke(check_messages)
        return self._parse_self_check_response(check_response.content) 