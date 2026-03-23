from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import json
import re
import asyncio

from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.schema import HumanMessage, SystemMessage

from services.repair_loop.prompts import FINSTAT_INITIAL_TEMPLATE, FINSTAT_REFINE_TEMPLATE
from services.repair_loop import verification_agent
from rag.rag import SchemaRAG


REPAIR_HISTORY_KEY_PREFIX = "repair:session:"


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
                    history.append(json.loads(item))
                except (json.JSONDecodeError, Exception):
                    continue
            return history
        except Exception:
            return []

    def _store_attempt(self, session_id: str, attempt: Dict) -> None:
        try:
            key = f"{REPAIR_HISTORY_KEY_PREFIX}{session_id}"
            self.redis.rpush(key, json.dumps(attempt))
            self.redis.expire(key, self.redis_ttl)
        except Exception as e:
            print(f"Warning: Failed to store attempt in Redis: {e}")

    def _format_history_for_prompt(self, history: List[Dict]) -> str:
        if not history:
            return "No previous attempts."
        
        formatted = []
        for i, attempt in enumerate(history, 1):
            attempt_num = attempt.get("attempt", i)
            error = attempt.get("error", "Unknown error")
            sql = attempt.get("sql", "N/A")
            error_type = attempt.get("type", "UNKNOWN")
            formatted.append(
                f"Attempt {attempt_num} ({error_type}):\n"
                f"  Error: {error}\n"
                f"  Failed SQL: {sql[:200]}..."
            )
        return "\n\n".join(formatted)

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
        attempt_history: List[Dict]
    ) -> str:
        history_str = self._format_history_for_prompt(attempt_history)
        
        prompt = FINSTAT_REFINE_TEMPLATE.format_messages(
            question=question,
            schema_context=schema_context,
            previous_sql=failed_sql,
            error_message=error,
            attempt_history=history_str,
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
                        error=final_error,
                        schema_context=schema_context,
                        attempt_history=attempt_history
                    )
            except Exception as e:
                attempt += 1
                attempt_history.append({
                    "attempt": attempt,
                    "error": f"SQL generation failed: {str(e)}",
                    "sql": current_sql or "N/A",
                    "type": "GENERATION_ERROR"
                })
                self._store_attempt(str(session_id), attempt_history[-1])
                continue
            
            result, error = await self._execute_sql(current_sql)
            
            if error is not None:
                attempt += 1
                final_error = error
                attempt_history.append({
                    "attempt": attempt,
                    "error": error,
                    "sql": current_sql,
                    "type": "EXECUTION_ERROR"
                })
                self._store_attempt(str(session_id), attempt_history[-1])
                continue
            
            verification = await verification_agent.logic_verification_agent(
                sql=current_sql,
                results=result,
                question=question
            )
            
            if verification["is_valid"]:
                return {
                    "sql_query": current_sql,
                    "query_result": result,
                    "success": True,
                    "attempts": attempt + 1,
                    "error": None,
                }
            else:
                attempt += 1
                final_error = verification["feedback"]
                attempt_history.append({
                    "attempt": attempt,
                    "error": final_error,
                    "sql": current_sql,
                    "type": "LOGIC_ERROR"
                })
                self._store_attempt(str(session_id), attempt_history[-1])
                continue
        
        return {
            "sql_query": current_sql,
            "query_result": None,
            "success": False,
            "attempts": self.max_retries,
            "error": "MAX_RETRIES_EXCEEDED",
            "session_history": attempt_history,
        }
