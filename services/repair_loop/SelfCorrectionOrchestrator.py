from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import json
import re
import asyncio
from datetime import datetime

from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.schema import HumanMessage, SystemMessage

from services.repair_loop.prompts import FINSTAT_INITIAL_TEMPLATE, FINSTAT_REFINE_TEMPLATE
from auto_correction.logic_verification_agent import LogicVerificationAgent
from rag.rag import SchemaRAG


REPAIR_HISTORY_KEY_PREFIX = "repair_history:session:"
TOKEN_THRESHOLD = 2000
MAX_KEEP_ATTEMPTS = 4


@dataclass
class OrchestratorState:
    current_sql: str = ""
    attempt_count: int = 0
    error: Optional[str] = None
    verification_result: Optional[Dict] = None
    session_history: List[Dict] = field(default_factory=list)


class SelfCorrectionOrchestrator:
    def __init__(
        self,
        llm,
        db,
        redis_client,
        max_retries: int = 3,
        use_rag: bool = True,
        redis_ttl: int = 3600,
        execute_tool=None,
    ):
        self.llm = llm
        self.db = db
        self.redis = redis_client
        self.max_retries = max_retries
        self.use_rag = use_rag
        self.redis_ttl = redis_ttl

        self.schema_rag = SchemaRAG() if use_rag else None
        self._execute_tool = execute_tool or QuerySQLDataBaseTool(db=db)
        self.logic_verifier = LogicVerificationAgent(llm)

    def _get_schema_context(self, question: str) -> str:
        if self.use_rag and self.schema_rag and self.schema_rag.is_initialized():
            table_info = self.schema_rag.get_table_info_for_rag(question)
            if table_info:
                return table_info
        return self.db.get_table_info()

    def _get_attempt_history(self, session_id: str) -> List[Dict]:
        try:
            key = f"{REPAIR_HISTORY_KEY_PREFIX}{session_id}"
            history_json = self.redis.lrange(key, 0, -1)
            if not history_json:
                return []
            
            history = []
            for item in history_json:
                try:
                    entry = json.loads(item)
                    # Validate new format - must have attempt_number
                    if "attempt_number" not in entry:
                        # Old format detected - reset history
                        self._clear_history(session_id)
                        return []
                    history.append(entry)
                except (json.JSONDecodeError, Exception):
                    # Invalid JSON - reset history
                    self._clear_history(session_id)
                    return []
            return history
        except Exception:
            return []

    def _clear_history(self, session_id: str) -> None:
        """Clear history if old format detected."""
        try:
            key = f"{REPAIR_HISTORY_KEY_PREFIX}{session_id}"
            self.redis.delete(key)
            print(f"Cleared old-format history for session: {session_id}")
        except Exception:
            pass

    def _store_attempt(self, session_id: str, attempt: Dict) -> None:
        try:
            key = f"{REPAIR_HISTORY_KEY_PREFIX}{session_id}"
            # Ensure entry has required fields for new format
            entry = {
                "attempt_number": attempt.get("attempt_number", attempt.get("attempt", 1)),
                "sql": attempt.get("sql", ""),
                "error": attempt.get("error", ""),
                "logic_feedback": attempt.get("logic_feedback", ""),
                "type": attempt.get("type", "UNKNOWN"),
                "timestamp": attempt.get("timestamp", datetime.utcnow().isoformat())
            }
            self.redis.rpush(key, json.dumps(entry))
            self.redis.expire(key, self.redis_ttl)
        except Exception as e:
            print(f"Warning: Failed to store attempt in Redis: {e}")

    def _format_history_for_prompt(self, history: List[Dict]) -> str:
        if not history:
            return "No previous attempts."
        
        formatted = []
        for attempt in history:
            attempt_num = attempt.get("attempt_number", attempt.get("attempt", "?"))
            error = attempt.get("error", "Unknown error")
            sql = attempt.get("sql", "N/A")
            error_type = attempt.get("type", "UNKNOWN")
            formatted.append(
                f"Attempt {attempt_num} ({error_type}):\n"
                f"  Error: {error}\n"
                f"  Failed SQL: {sql[:200]}..."
            )
        return "\n\n".join(formatted)

    def _format_past_attempts(self, history: List[Dict]) -> str:
        """Format history into detailed Past Attempts section for prompt."""
        if not history:
            return "No previous attempts in this session."
        
        formatted = []
        for entry in history:
            attempt_num = entry.get("attempt_number", "?")
            sql = entry.get("sql", "N/A")
            error_type = entry.get("type", "UNKNOWN")
            
            # Get appropriate error/feedback
            if error_type == "LOGIC_ERROR":
                feedback = entry.get("logic_feedback", "No logic feedback.")
            else:
                feedback = entry.get("error", "Unknown error.")
            
            formatted.append(
                f"### Attempt {attempt_num} ({error_type})\n"
                f"SQL: ```sql\n{sql}\n```\n"
                f"Error/Feedback: {feedback[:300]}...\n"
            )
        
        return "\n\n".join(formatted)

    def _trim_history(self, history: List[Dict], max_attempts: int = MAX_KEEP_ATTEMPTS) -> List[Dict]:
        """
        Trim history to stay within 2000 token threshold.
        Keep: First attempt (original) + most recent failures.
        """
        if len(history) <= max_attempts:
            return history
        
        # Keep first (original attempt), drop middle, keep recent
        trimmed = [history[0]] + history[-(max_attempts-1):]
        print(f"Trimmed history from {len(history)} to {len(trimmed)} entries (token threshold: {TOKEN_THRESHOLD})")
        return trimmed

    def _extract_sql_from_response(self, response_content: str) -> str:
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        sql_match = re.search(r"### Corrected SQL:\s*```sql\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        return response_content.strip()

    async def _generate_sql(
        self,
        question: str,
        schema_context: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        prompt = FINSTAT_INITIAL_TEMPLATE.format_messages(
            schema_context=schema_context,
            question=question,
        )
        
        max_retries = 5
        timeout_seconds = 25
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt),
                    timeout=timeout_seconds
                )
                return self._extract_sql_from_response(response.content)
            except asyncio.TimeoutError:
                last_exception = asyncio.TimeoutError(f"LLM call timed out after {timeout_seconds}s")
            except Exception as e:
                last_exception = e
                break
        
        raise last_exception or Exception("Failed to generate SQL after retries")

    async def _refine_sql(
        self,
        question: str,
        failed_sql: str,
        error: str,
        schema_context: str,
        attempt_history: List[Dict],
        logic_feedback: Optional[str] = None
    ) -> str:
        history_str = self._format_history_for_prompt(attempt_history)
        past_attempts_str = self._format_past_attempts(attempt_history)
        
        # Determine latest feedback
        latest_feedback = logic_feedback if logic_feedback else error
        
        # Apply token trimming if history is too long
        trimmed_history = self._trim_history(attempt_history)
        
        prompt = FINSTAT_REFINE_TEMPLATE.format_messages(
            question=question,
            schema_context=schema_context,
            previous_sql=failed_sql,
            latest_feedback=latest_feedback,
            past_attempts=past_attempts_str,
        )
        
        max_retries = 5
        timeout_seconds = 25
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt),
                    timeout=timeout_seconds
                )
                return self._extract_sql_from_response(response.content)
            except asyncio.TimeoutError:
                last_exception = asyncio.TimeoutError(f"LLM call timed out after {timeout_seconds}s")
            except Exception as e:
                last_exception = e
                break
        
        raise last_exception or Exception("Failed to refine SQL after retries")

    async def _execute_sql(self, sql: str) -> Tuple[Any, Optional[str]]:
        try:
            result = self._execute_tool.invoke({"query": sql})
            return result, None
        except Exception as e:
            return None, str(e)

    async def execute(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        attempt = 0
        current_sql = None
        final_result = None
        final_error = None
        logic_feedback = None
        
        schema_context = self._get_schema_context(question)
        attempt_history = self._get_attempt_history(str(session_id))
        
        while attempt < self.max_retries:
            try:
                if attempt == 0:
                    current_sql = await self._generate_sql(
                        question=question,
                        schema_context=schema_context,
                        history=attempt_history
                    )
                else:
                    current_sql = await self._refine_sql(
                        question=question,
                        failed_sql=current_sql,
                        error=final_error if final_error else "N/A",
                        schema_context=schema_context,
                        attempt_history=attempt_history,
                        logic_feedback=logic_feedback
                    )
            except Exception as e:
                attempt += 1
                attempt_history.append({
                    "attempt_number": attempt,
                    "error": f"SQL generation failed: {str(e)}",
                    "sql": current_sql or "N/A",
                    "logic_feedback": "",
                    "type": "GENERATION_ERROR",
                    "timestamp": datetime.utcnow().isoformat()
                })
                self._store_attempt(str(session_id), attempt_history[-1])
                continue
            
            result, error = await self._execute_sql(current_sql)
            
            if error is not None:
                attempt += 1
                final_error = error
                attempt_history.append({
                    "attempt_number": attempt,
                    "error": error,
                    "sql": current_sql,
                    "logic_feedback": "",
                    "type": "EXECUTION_ERROR",
                    "timestamp": datetime.utcnow().isoformat()
                })
                self._store_attempt(str(session_id), attempt_history[-1])
                continue
            
            try:
                matches_intent, corrected_sql, metadata = await self.logic_verifier.verify(
                    current_sql=current_sql,
                    user_query=question,
                    execution_result=result,
                )
                
                if matches_intent:
                    return {
                        "sql_query": current_sql,
                        "query_result": result,
                        "success": True,
                        "attempts": attempt + 1,
                        "error": None,
                    }
                else:
                    logic_feedback = f"{metadata.get('explanation', 'Logic verification failed.')}"
                    if corrected_sql:
                        logic_feedback += f"\n\nSuggested SQL: {corrected_sql}"
                    
                    attempt += 1
                    final_error = logic_feedback
                    attempt_history.append({
                        "attempt_number": attempt,
                        "error": "",
                        "sql": current_sql,
                        "logic_feedback": logic_feedback,
                        "type": "LOGIC_ERROR",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    self._store_attempt(str(session_id), attempt_history[-1])
                    continue
            except Exception as e:
                print(f"Warning: Logic verification failed: {e}")
                return {
                    "sql_query": current_sql,
                    "query_result": result,
                    "success": True,
                    "attempts": attempt + 1,
                    "error": None,
                }
        
        return {
            "sql_query": current_sql,
            "query_result": None,
            "success": False,
            "attempts": self.max_retries,
            "error": "MAX_RETRIES_EXCEEDED",
            "session_history": attempt_history,
        }
