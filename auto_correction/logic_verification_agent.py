"""
Logic Verification Agent (Week 10 Deliverable)

Based on the FinStat2SQL paper's methodology, this module implements a Logical Critic
that verifies whether a successfully executed SQL query matches the user's original intent.

While execution checks (e.g., AutoCorrection) catch syntax errors, this agent catches
logical errors where the query doesn't capture the user's true intent or returns empty
results when it shouldn't.
"""

import logging
import asyncio
from typing import Tuple, Dict, Any
from config.prompts import LOGIC_VERIFICATION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class LogicVerificationAgent:
    """
    Week 10 Deliverable: Logic Verification Agent (Logical Critic)
    
    Evaluates a successfully executed SQL query to ensure it matches the user's intent
    and returns valid data. Based on the FinStat2SQL self-correction methodology.
    """

    def __init__(self, llm):
        """
        Initialize the Logic Verification Agent.
        
        Args:
            llm: The language model instance (ChatOpenAI or similar)
        """
        self.llm = llm

    def _format_execution_result(self, execution_result: Any) -> str:
        """
        Format execution result into a readable string for the LLM.
        
        Args:
            execution_result: The result from SQL execution (list, dict, str, etc.)
            
        Returns:
            A formatted string representation of the result
        """
        if execution_result is None:
            return "[No result]"
        elif isinstance(execution_result, str):
            return execution_result
        elif isinstance(execution_result, (list, tuple)):
            if not execution_result:
                return "[Empty result set]"
            # Format first few rows for readability
            result_str = ""
            for i, row in enumerate(execution_result[:10]):
                result_str += f"Row {i + 1}: {row}\n"
            if len(execution_result) > 10:
                result_str += f"... ({len(execution_result) - 10} more rows)"
            return result_str
        elif isinstance(execution_result, dict):
            if not execution_result:
                return "[Empty result dict]"
            result_str = ""
            for key, value in list(execution_result.items())[:10]:
                result_str += f"{key}: {value}\n"
            return result_str
        else:
            return str(execution_result)[:500]  # Limit output length

    def _parse_verification_response(self, response_text: str) -> Tuple[bool, str, str]:
        """
        Parse the FinStat2SQL structured output from the LLM.
        
        Args:
            response_text: The raw response from the LLM
            
        Returns:
            Tuple of (matches_intent: bool, reasoning: str, new_sql: str)
        """
        decision = ""
        reasoning = ""
        new_sql = ""
        in_sql_block = False

        # Parse the structured output format
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("### Decision:"):
                decision = line.replace("### Decision:", "").strip().upper()
            elif line.startswith("### Reasoning:"):
                reasoning = line.replace("### Reasoning:", "").strip()
            elif line.startswith("### SQL Query:"):
                # Handle both inline and multiline SQL
                sql_content = line.replace("### SQL Query:", "").strip()
                if sql_content.startswith("```sql"):
                    in_sql_block = True
                    new_sql = ""
                elif sql_content.startswith("```") and in_sql_block:
                    in_sql_block = False
                else:
                    new_sql = sql_content
            elif in_sql_block:
                if line.startswith("```"):
                    in_sql_block = False
                else:
                    new_sql += line + "\n"
            elif new_sql and line.startswith("```"):
                # End of SQL block
                in_sql_block = False

        # Clean up the SQL
        new_sql = new_sql.strip()
        new_sql = new_sql.replace("```sql", "").replace("```", "").strip()

        matches_intent = decision == "YES"
        return matches_intent, reasoning, new_sql

    async def verify(
        self,
        current_sql: str,
        user_query: str,
        execution_result: Any,
        timeout_seconds: int = 25,
        max_retries: int = 3,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verify if a successfully executed SQL query matches the user's intent.
        
        This is the main entry point for the Logic Verification Agent.
        
        Args:
            current_sql: The SQL query that was executed
            user_query: The original natural language query from the user
            execution_result: The result returned from executing the query
            timeout_seconds: Timeout for LLM call (default 25 seconds)
            max_retries: Maximum retry attempts for LLM call (default 3)
            
        Returns:
            Tuple containing:
            - matches_intent (bool): Whether the query matches user intent
            - new_sql (str): Corrected SQL if needed (empty string if no correction)
            - metadata (dict): Verification metadata including explanation and potential issues
        """
        logger.info("Running Logic Verification Agent (Intent Match)...")

        # 1. Format the FinStat2SQL prompt
        formatted_result = self._format_execution_result(execution_result)
        prompt = LOGIC_VERIFICATION_PROMPT_TEMPLATE.format_messages(
            user_query=user_query, sql_result=formatted_result
        )

        # 2. Call the LLM with retry logic
        response_text = None
        last_exception = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting logic verification LLM call (Attempt {attempt + 1}/{max_retries})..."
                )
                response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt), timeout=timeout_seconds
                )
                response_text = response.content
                logger.info(f"Logic verification LLM call successful (Attempt {attempt + 1}).")
                break
            except asyncio.TimeoutError:
                logger.warning(
                    f"Logic verification LLM call timed out after {timeout_seconds}s (Attempt {attempt + 1}). Retrying..."
                )
                last_exception = asyncio.TimeoutError(
                    f"Logic verification LLM call timed out after {max_retries} attempts."
                )
            except Exception as e:
                logger.error(
                    f"Logic verification LLM call failed with error on attempt {attempt + 1}: {e}"
                )
                last_exception = e
                break

        if response_text is None:
            if last_exception:
                raise last_exception
            else:
                raise Exception(
                    "Logic verification LLM call failed after retries for unknown reason."
                )

        # 3. Parse the FinStat2SQL structured output
        matches_intent, reasoning, new_sql = self._parse_verification_response(response_text)

        # 4. Detect potential issues
        potential_issues = []
        if not execution_result or (isinstance(execution_result, (list, dict)) and not execution_result):
            potential_issues.append("Empty result table")
        if not reasoning:
            potential_issues.append("Unable to provide reasoning")

        # 5. Format output aligned with LLM Chatbot 2 baseline's 'self_check' metadata
        verification_metadata = {
            "explanation": reasoning,
            "matches_intent": matches_intent,
            "potential_issues": potential_issues,
        }

        if matches_intent:
            logger.info("Logic Verification Passed: Query matches user intent.")
            return True, "", verification_metadata
        else:
            logger.warning("Logic Verification Failed: Triggering re-generation.")
            return False, new_sql, verification_metadata


async def logic_verification_agent(
    current_sql: str,
    user_query: str,
    execution_result: Any,
    llm_client,
    timeout_seconds: int = 25,
    max_retries: int = 3,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Standalone async function for Logic Verification Agent.
    
    This is a convenience wrapper for direct use without instantiating the class.
    
    Args:
        current_sql: The SQL query that was executed
        user_query: The original natural language query from the user
        execution_result: The result returned from executing the query
        llm_client: The LLM client instance
        timeout_seconds: Timeout for LLM call (default 25 seconds)
        max_retries: Maximum retry attempts for LLM call (default 3)
        
    Returns:
        Tuple containing:
        - matches_intent (bool): Whether the query matches user intent
        - new_sql (str): Corrected SQL if needed (empty string if no correction)
        - metadata (dict): Verification metadata including explanation and potential issues
    """
    agent = LogicVerificationAgent(llm_client)
    return await agent.verify(
        current_sql=current_sql,
        user_query=user_query,
        execution_result=execution_result,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
