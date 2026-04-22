#!/usr/bin/env python3
"""
NORP Repair Loop - Evaluation Demo
Quick demonstration of evaluation system capabilities
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from evaluation_system import RepairLoopEvaluator
from config.config import Config
from services.llm_manager.LLMManager import LLMManager
from services.redis_manager.RedisManager import RedisManager
from services.sql_manager.DatabaseManager import DatabaseManager


class MockEvaluationResult:
    """Mock evaluation result for demonstration."""
    def __init__(self, success, attempts, execution_time, error=None):
        self.success = success
        self.attempts = attempts
        self.execution_time = execution_time
        self.error = error

    def __dict__(self):
        return {
            'success': self.success,
            'attempts': self.attempts,
            'execution_time': self.execution_time,
            'error': self.error
        }


class MockEvaluator:
    """Mock evaluator that simulates evaluation results."""

    async def evaluate_single_question(self, question, use_new_system=True):
        """Mock evaluation of a single question."""
        import random
        import time

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Mock results - new system performs better
        if use_new_system:
            # New system: 80% success rate, average 2.1 attempts
            success = random.random() < 0.8
            attempts = random.randint(1, 4) if success else random.randint(2, 5)
        else:
            # Legacy system: 65% success rate, average 2.8 attempts
            success = random.random() < 0.65
            attempts = random.randint(1, 5) if success else random.randint(3, 6)

        execution_time = random.uniform(0.5, 3.0)
        error = "Mock error: Query failed" if not success else None

        return MockEvaluationResult(success, attempts, execution_time, error)


async def demo_evaluation_system():
    """Demonstrate the evaluation system with a few key examples."""

    print("🎯 NORP Repair Loop - Evaluation System Demo")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("📋 This demo shows how the evaluation system compares:")
    print("   • NEW: History-Aware Repair Loop (Week 11)")
    print("   • OLD: Legacy Baseline (pre-Week 11)")
    print()

    print("⚠️  Note: This demo runs without API keys for demonstration purposes")
    print("   Real evaluation requires NVIDIA_API_KEY environment variable")
    print()

    try:
        # Initialize components (mock for demo)
        print("🔧 Initializing components...")
        config = Config()

        # Mock components for demonstration
        print("📝 Using mock components for demo (no API calls)")

        # Create mock evaluator for demo
        evaluator = MockEvaluator()
        print("✅ Mock components ready")
        print()

        # Demo questions that highlight different scenarios
        demo_questions = [
            {
                "question": "How many crime incidents were reported in 2023?",
                "category": "Simple Count Query",
                "expected_improvement": "History-aware system should perform similarly but with better error recovery"
            },
            {
                "question": "What are the top 5 crime types in Atlanta?",
                "category": "Complex Aggregation",
                "expected_improvement": "History tracking helps avoid repeated mistakes in complex queries"
            },
            {
                "question": "Show me demographic data for zip code 30005",
                "category": "Data Filtering",
                "expected_improvement": "Context from previous attempts improves accuracy"
            }
        ]

        print("🧪 Running evaluation demo...")
        print()

        all_new_results = []
        all_baseline_results = []

        for i, q_info in enumerate(demo_questions, 1):
            print(f"Test {i}: {q_info['category']}")
            print(f"Question: {q_info['question']}")
            print(f"Expected: {q_info['expected_improvement']}")
            print("-" * 50)

            # Test new system
            print("🆕 Testing NEW History-Aware System...")
            new_result = await evaluator.evaluate_single_question(q_info['question'], use_new_system=True)
            all_new_results.append(new_result)

            status = "✅ SUCCESS" if new_result.success else "❌ FAILED"
            print(f"   Result: {status}")
            print(f"   Attempts: {new_result.attempts}")
            print(".2f")
            if new_result.error:
                print(f"   Error: {new_result.error}")
            print()

            # Test baseline
            print("📊 Testing LEGACY Baseline System...")
            baseline_result = await evaluator.evaluate_single_question(q_info['question'], use_new_system=False)
            all_baseline_results.append(baseline_result)

            status = "✅ SUCCESS" if baseline_result.success else "❌ FAILED"
            print(f"   Result: {status}")
            print(f"   Attempts: {baseline_result.attempts}")
            print(".2f")
            if baseline_result.error:
                print(f"   Error: {baseline_result.error}")
            print()

            # Quick comparison
            print("⚖️  COMPARISON:")
            if new_result.success and not baseline_result.success:
                print("   🏆 NEW SYSTEM ADVANTAGE: Fixed baseline failure")
            elif baseline_result.success and not new_result.success:
                print("   📉 BASELINE ADVANTAGE: New system regressed")
            elif new_result.success and baseline_result.success:
                if new_result.attempts < baseline_result.attempts:
                    savings = baseline_result.attempts - new_result.attempts
                    print(f"   🎯 NEW SYSTEM MORE EFFICIENT: {savings} fewer attempts")
                elif new_result.attempts > baseline_result.attempts:
                    extra = new_result.attempts - baseline_result.attempts
                    print(f"   🤔 BASELINE MORE EFFICIENT: {extra} fewer attempts")
                else:
                    print("   🤝 EQUAL EFFICIENCY: Same number of attempts")
            else:
                print("   💥 BOTH FAILED: Needs investigation")
            print()

        # Summary
        print("=" * 60)
        print("📊 DEMO SUMMARY")
        print("=" * 60)

        new_successes = sum(1 for r in all_new_results if r.success)
        baseline_successes = sum(1 for r in all_baseline_results if r.success)

        print(f"Questions Tested: {len(demo_questions)}")
        print(f"New System Successes: {new_successes}/{len(demo_questions)} ({new_successes/len(demo_questions)*100:.1f}%)")
        print(f"Baseline Successes: {baseline_successes}/{len(demo_questions)} ({baseline_successes/len(demo_questions)*100:.1f}%)")

        new_avg_attempts = sum(r.attempts for r in all_new_results) / len(all_new_results)
        baseline_avg_attempts = sum(r.attempts for r in all_baseline_results) / len(all_baseline_results)

        print(".2f")
        print(".2f")

        improvement = new_successes - baseline_successes
        if improvement > 0:
            print(f"🎉 RESULT: New system shows improvement (+{improvement} more successes)")
        elif improvement < 0:
            print(f"⚠️  RESULT: New system shows regression ({improvement} fewer successes)")
        else:
            print("🤝 RESULT: Systems perform equally in this demo")

        print()
        print("📝 NOTES:")
        print("• This is a small demo - full evaluation uses 13+ questions")
        print("• Real improvements may be more/less pronounced with larger datasets")
        print("• Run 'python3 run_comprehensive_evaluation.py' for full evaluation")
        print("• Results saved to evaluation_demo_results.json")

        # Save demo results
        demo_results = {
            "demo_timestamp": datetime.now().isoformat(),
            "questions_tested": len(demo_questions),
            "new_system_results": [r.__dict__ for r in all_new_results],
            "baseline_results": [r.__dict__ for r in all_baseline_results],
            "summary": {
                "new_success_rate": new_successes / len(demo_questions),
                "baseline_success_rate": baseline_successes / len(demo_questions),
                "new_avg_attempts": new_avg_attempts,
                "baseline_avg_attempts": baseline_avg_attempts
            }
        }

        with open("evaluation_demo_results.json", "w") as f:
            import json
            json.dump(demo_results, f, indent=2, default=str)

        print("💾 Demo results saved to: evaluation_demo_results.json")

    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def show_evaluation_features():
    """Show the key features of the evaluation system."""

    print("🔍 NORP Repair Loop - Evaluation System Features")
    print("=" * 60)

    features = [
        "📊 Comprehensive Metrics",
        "  • Success rates comparison",
        "  • Attempt count analysis",
        "  • Execution time measurement",
        "  • Query-by-query breakdown",

        "🔬 Scientific Methodology",
        "  • Same questions for both systems",
        "  • Controlled environment",
        "  • Statistical analysis",
        "  • Reproducible results",

        "📈 Performance Tracking",
        "  • Identifies improvements",
        "  • Detects regressions",
        "  • Quantifies efficiency gains",
        "  • Supports data-driven decisions",

        "💾 Result Persistence",
        "  • JSON data export",
        "  • Markdown reports",
        "  • Historical tracking",
        "  • Shareable evidence"
    ]

    for feature in features:
        print(feature)

    print()
    print("🚀 Usage:")
    print("  python3 run_evaluation_demo.py          # Quick demo")
    print("  python3 run_comprehensive_evaluation.py # Full evaluation")
    print("  python3 evaluation_system.py            # Direct API usage")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--features":
        asyncio.run(show_evaluation_features())
    else:
        asyncio.run(demo_evaluation_system())