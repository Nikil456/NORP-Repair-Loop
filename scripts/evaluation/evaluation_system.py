#!/usr/bin/env python3
"""
NORP Repair Loop - Evaluation and Metrics System
Compares repair loop performance with legacy baseline to ensure improvements
"""

import asyncio
import json
import time
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import statistics
from datetime import datetime

from services.repair_loop.SelfCorrectionOrchestrator import SelfCorrectionOrchestrator


@dataclass
class EvaluationResult:
    """Result of a single evaluation run."""
    question: str
    success: bool
    attempts: int
    execution_time: float
    final_sql: str
    error: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class BaselineResult:
    """Legacy baseline implementation result."""
    question: str
    success: bool
    attempts: int
    execution_time: float
    final_sql: str
    error: Optional[str] = None


class LegacyBaselineOrchestrator:
    """Simplified baseline implementation without history-aware refinement."""

    def __init__(self, llm, db, redis_client, max_retries: int = 3):
        self.llm = llm
        self.db = db
        self.redis = redis_client
        self.max_retries = max_retries

    def _get_schema_context(self, question: str) -> str:
        return self.db.get_table_info()

    async def _generate_sql(self, question: str, schema_context: str) -> str:
        from services.repair_loop.prompts import FINSTAT_INITIAL_TEMPLATE

        prompt = FINSTAT_INITIAL_TEMPLATE.format_messages(
            schema_context=schema_context,
            question=question,
        )

        response = await self.llm.ainvoke(prompt)
        return self._extract_sql_from_response(response.content)

    async def _refine_sql(self, question: str, failed_sql: str, error: str,
                         schema_context: str) -> str:
        from services.repair_loop.prompts import FINSTAT_REFINE_TEMPLATE

        prompt = FINSTAT_REFINE_TEMPLATE.format_messages(
            question=question,
            schema_context=schema_context,
            previous_sql=failed_sql,
            error_message=error,
            logic_feedback="No logic verification feedback provided.",
            attempt_history="No previous attempts.",
            past_attempts="No previous attempts.",
            latest_feedback="No additional feedback available.",
        )

        response = await self.llm.ainvoke(prompt)
        return self._extract_sql_from_response(response.content)

    def _extract_sql_from_response(self, response_content: str) -> str:
        import re
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        return response_content.strip()

    async def _execute_sql(self, sql: str) -> tuple:
        """Simple execution without data fetcher."""
        try:
            # Use basic SQLAlchemy execution
            with self.db._engine.connect() as conn:
                result = conn.execute(self.db._engine.text(sql))
                rows = result.fetchall()
                return [dict(row) for row in rows], None
        except Exception as e:
            return None, str(e)

    async def execute(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Legacy baseline execution without history tracking."""
        start_time = time.time()
        attempt = 0
        current_sql = None
        schema_context = self._get_schema_context(question)

        while attempt < self.max_retries:
            try:
                if attempt == 0:
                    current_sql = await self._generate_sql(question, schema_context)
                else:
                    current_sql = await self._refine_sql(question, current_sql,
                                                       "Previous attempt failed", schema_context)
            except Exception as e:
                attempt += 1
                continue

            result, error = await self._execute_sql(current_sql)

            if not error:
                execution_time = time.time() - start_time
                return {
                    "sql_query": current_sql,
                    "query_result": result,
                    "success": True,
                    "attempts": attempt + 1,
                    "execution_time": execution_time,
                    "error": None,
                }

            attempt += 1

        execution_time = time.time() - start_time
        return {
            "sql_query": current_sql,
            "query_result": None,
            "success": False,
            "attempts": self.max_retries,
            "execution_time": execution_time,
            "error": "MAX_RETRIES_EXCEEDED",
        }


@dataclass
class EvaluationResult:
    """Result of a single evaluation run."""
    question: str
    success: bool
    attempts: int
    execution_time: float
    final_sql: str
    error: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class BaselineResult:
    """Legacy baseline implementation result."""
    question: str
    success: bool
    attempts: int
    execution_time: float
    final_sql: str
    error: Optional[str] = None


class LegacyBaselineOrchestrator:
    """Simplified baseline implementation without history-aware refinement."""

    def __init__(self, llm, db, redis_client, max_retries: int = 3):
        self.llm = llm
        self.db = db
        self.redis = redis_client
        self.max_retries = max_retries

    def _get_schema_context(self, question: str) -> str:
        return self.db.get_table_info()

    async def _generate_sql(self, question: str, schema_context: str) -> str:
        from services.repair_loop.prompts import FINSTAT_INITIAL_TEMPLATE

        prompt = FINSTAT_INITIAL_TEMPLATE.format_messages(
            schema_context=schema_context,
            question=question,
        )

        response = await self.llm.ainvoke(prompt)
        return self._extract_sql_from_response(response.content)

    async def _refine_sql(self, question: str, failed_sql: str, error: str,
                         schema_context: str) -> str:
        from services.repair_loop.prompts import FINSTAT_REFINE_TEMPLATE

        prompt = FINSTAT_REFINE_TEMPLATE.format_messages(
            question=question,
            schema_context=schema_context,
            previous_sql=failed_sql,
            error_message=error,
            logic_feedback="No logic verification feedback provided.",
            attempt_history="No previous attempts.",
            past_attempts="No previous attempts.",
            latest_feedback="No additional feedback available.",
        )

        response = await self.llm.ainvoke(prompt)
        return self._extract_sql_from_response(response.content)

    def _extract_sql_from_response(self, response_content: str) -> str:
        import re
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        return response_content.strip()

    async def _execute_sql(self, sql: str) -> tuple:
        """Simple execution without data fetcher."""
        try:
            # Use basic SQLAlchemy execution
            with self.db._engine.connect() as conn:
                result = conn.execute(self.db._engine.text(sql))
                rows = result.fetchall()
                return [dict(row) for row in rows], None
        except Exception as e:
            return None, str(e)

    async def execute(self, question: str, session_id: str) -> Dict[str, Any]:
        """Legacy baseline execution without history tracking."""
        start_time = time.time()
        attempt = 0
        current_sql = None
        schema_context = self._get_schema_context(question)

        while attempt < self.max_retries:
            try:
                if attempt == 0:
                    current_sql = await self._generate_sql(question, schema_context)
                else:
                    current_sql = await self._refine_sql(question, current_sql,
                                                       "Previous attempt failed", schema_context)
            except Exception as e:
                attempt += 1
                continue

            result, error = await self._execute_sql(current_sql)

            if not error:
                execution_time = time.time() - start_time
                return {
                    "sql_query": current_sql,
                    "query_result": result,
                    "success": True,
                    "attempts": attempt + 1,
                    "execution_time": execution_time,
                    "error": None,
                }

            attempt += 1

        execution_time = time.time() - start_time
        return {
            "sql_query": current_sql,
            "query_result": None,
            "success": False,
            "attempts": self.max_retries,
            "execution_time": execution_time,
            "error": "MAX_RETRIES_EXCEEDED",
        }


class RepairLoopEvaluator:
    """Evaluates and compares repair loop performance with legacy baseline."""

    def __init__(self, llm, db, redis_client):
        self.llm = llm
        self.db = db
        self.redis_client = redis_client

        # Initialize both systems
        self.new_orchestrator = SelfCorrectionOrchestrator(
            llm=llm, db=db, redis_client=redis_client, max_retries=3
        )
        self.baseline_orchestrator = LegacyBaselineOrchestrator(
            llm=llm, db=db, redis_client=redis_client, max_retries=3
        )

    def get_evaluation_questions(self) -> List[str]:
        """Get a diverse set of test questions for evaluation."""
        return [
            "How many crime incidents were reported in 2023?",
            "What are the top 5 crime types in Atlanta?",
            "Show me demographic data for zip code 30005",
            "How many housing units are valued over $500,000?",
            "What is the average rent for housing units in zip code 30004?",
            "List all crime incidents that occurred on weekends",
            "Show housing data for areas with more than 1000 units",
            "What are the most common crime types by area?",
            "Display demographic information for Hispanic population",
            "Find housing units with rent between $1000 and $2000"
        ]

    async def evaluate_single_question(self, question: str, use_new_system: bool = True) -> EvaluationResult:
        """Evaluate a single question using either new or baseline system."""
        session_id = f"eval_{int(time.time())}_{hash(question) % 1000}"

        start_time = time.time()

        if use_new_system:
            result = await self.new_orchestrator.execute(question, session_id)
        else:
            result = await self.baseline_orchestrator.execute(question, session_id)

        execution_time = time.time() - start_time

        return EvaluationResult(
            question=question,
            success=result.get("success", False),
            attempts=result.get("attempts", 0),
            execution_time=execution_time,
            final_sql=result.get("sql_query", ""),
            error=result.get("error"),
            session_id=session_id
        )

    async def run_full_evaluation(self, questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive evaluation comparing new vs baseline systems."""
        if questions is None:
            questions = self.get_evaluation_questions()

        print(f"🔬 Starting Repair Loop Evaluation")
        print(f"📊 Testing {len(questions)} questions")
        print(f"⚡ Comparing New System (History-Aware) vs Legacy Baseline")
        print("-" * 60)

        new_results = []
        baseline_results = []

        for i, question in enumerate(questions, 1):
            print(f"Testing Question {i}/{len(questions)}: {question[:50]}...")

            # Test new system
            new_result = await self.evaluate_single_question(question, use_new_system=True)
            new_results.append(new_result)

            # Test baseline
            baseline_result = await self.evaluate_single_question(question, use_new_system=False)
            baseline_results.append(baseline_result)

            print(f"  ✅ New: {new_result.success} ({new_result.attempts} attempts, {new_result.execution_time:.2f}s)")
            print(f"  📊 Baseline: {baseline_result.success} ({baseline_result.attempts} attempts, {baseline_result.execution_time:.2f}s)")

        # Calculate metrics
        metrics = self._calculate_metrics(new_results, baseline_results)

        # Generate report
        report = self._generate_evaluation_report(metrics, new_results, baseline_results)

        return {
            "metrics": metrics,
            "new_results": [r.__dict__ for r in new_results],
            "baseline_results": [r.__dict__ for r in baseline_results],
            "report": report,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_metrics(self, new_results: List[EvaluationResult],
                          baseline_results: List[BaselineResult]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""

        def calculate_stats(results):
            successes = [r for r in results if r.success]
            return {
                "total_questions": len(results),
                "successful_queries": len(successes),
                "success_rate": len(successes) / len(results) * 100,
                "avg_attempts": statistics.mean([r.attempts for r in results]),
                "avg_attempts_successful": statistics.mean([r.attempts for r in successes]) if successes else 0,
                "avg_execution_time": statistics.mean([r.execution_time for r in results]),
                "avg_execution_time_successful": statistics.mean([r.execution_time for r in successes]) if successes else 0,
            }

        new_stats = calculate_stats(new_results)
        baseline_stats = calculate_stats(baseline_results)

        return {
            "new_system": new_stats,
            "baseline_system": baseline_stats,
            "improvements": {
                "success_rate_improvement": new_stats["success_rate"] - baseline_stats["success_rate"],
                "attempts_reduction": baseline_stats["avg_attempts"] - new_stats["avg_attempts"],
                "time_improvement": baseline_stats["avg_execution_time"] - new_stats["avg_execution_time"],
            }
        }

    def _generate_evaluation_report(self, metrics: Dict, new_results: List[EvaluationResult],
                                   baseline_results: List[BaselineResult]) -> str:
        """Generate a comprehensive evaluation report."""

        report = f"""
# NORP Repair Loop - Evaluation Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

The evaluation compared the new History-Aware Repair Loop system against a legacy baseline
across {metrics['new_system']['total_questions']} diverse SQL generation tasks.

## Performance Metrics

### Success Rates
- **New System:** {metrics['new_system']['success_rate']:.1f}%
- **Legacy Baseline:** {metrics['baseline_system']['success_rate']:.1f}%
- **Improvement:** {metrics['improvements']['success_rate_improvement']:+.1f} percentage points

### Efficiency Metrics
- **Average Attempts (New):** {metrics['new_system']['avg_attempts']:.2f}
- **Average Attempts (Baseline):** {metrics['baseline_system']['avg_attempts']:.2f}
- **Attempts Reduction:** {metrics['improvements']['attempts_reduction']:+.2f} fewer attempts

### Execution Times
- **Average Time (New):** {metrics['new_system']['avg_execution_time']:.2f}s
- **Average Time (Baseline):** {metrics['baseline_system']['avg_execution_time']:.2f}s
- **Time Improvement:** {metrics['improvements']['time_improvement']:+.2f}s

## Detailed Results

### New System Performance
- Total Queries: {metrics['new_system']['total_questions']}
- Successful: {metrics['new_system']['successful_queries']}
- Success Rate: {metrics['new_system']['success_rate']:.1f}%

### Baseline System Performance
- Total Queries: {metrics['baseline_system']['total_questions']}
- Successful: {metrics['baseline_system']['successful_queries']}
- Success Rate: {metrics['baseline_system']['success_rate']:.1f}%

## Conclusion

{'✅ **SUCCESS:** The new History-Aware Repair Loop shows significant improvements over the legacy baseline.' if metrics['improvements']['success_rate_improvement'] > 0 else '❌ **CONCERN:** The new system does not show improvement over the baseline.'}

Key improvements include:
- {'Higher success rate' if metrics['improvements']['success_rate_improvement'] > 0 else 'No success rate improvement'}
- {'Fewer refinement attempts needed' if metrics['improvements']['attempts_reduction'] > 0 else 'No reduction in attempts'}
- {'Faster execution times' if metrics['improvements']['time_improvement'] > 0 else 'No time improvement'}

## Recommendations

{'🎉 **ROLL OUT:** The new system is ready for production deployment.' if all([
    metrics['improvements']['success_rate_improvement'] > 5,
    metrics['improvements']['attempts_reduction'] > 0.2,
    metrics['new_system']['success_rate'] > 70
]) else '🔄 **REVIEW:** Further optimization may be needed before production deployment.'}
"""

        return report

    def save_evaluation_results(self, results: Dict[str, Any], filename: str = None):
        """Save evaluation results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"📁 Evaluation results saved to: {filename}")
        return filename


async def main():
    """Run the evaluation system."""
    # This would be initialized with actual LLM, DB, Redis in real usage
    print("🔬 NORP Repair Loop - Evaluation System")
    print("This script evaluates the new History-Aware Repair Loop against legacy baseline")
    print()
    print("To run evaluation:")
    print("1. Initialize LLM, database, and Redis connections")
    print("2. Create RepairLoopEvaluator instance")
    print("3. Call evaluator.run_full_evaluation()")
    print("4. Review metrics and save results")
    print()
    print("Example usage:")
    print("""
    evaluator = RepairLoopEvaluator(llm, db, redis_client)
    results = await evaluator.run_full_evaluation()
    evaluator.save_evaluation_results(results)
    """)


if __name__ == "__main__":
    asyncio.run(main())