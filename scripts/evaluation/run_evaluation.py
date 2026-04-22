#!/usr/bin/env python3
"""
NORP Repair Loop - Evaluation Test Script
Demonstrates the evaluation system comparing new vs baseline performance
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


async def run_evaluation_demo():
    """Run a demonstration of the evaluation system."""

    print("🔬 NORP Repair Loop - Evaluation System Demo")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Initialize components
        print("🔧 Initializing components...")

        config = Config()
        llm_manager = LLMManager(config)
        redis_manager = RedisManager(config)
        db_manager = DatabaseManager(config)

        # Get the LLM client
        llm = llm_manager.get_client()

        # Create evaluator
        evaluator = RepairLoopEvaluator(
            llm=llm,
            db=db_manager,
            redis_client=redis_manager.client
        )

        print("✅ Components initialized successfully")
        print()

        # Run evaluation with a subset of questions for demo
        demo_questions = [
            "How many crime incidents were reported in 2023?",
            "What are the top 5 crime types in Atlanta?",
            "Show me demographic data for zip code 30005"
        ]

        print(f"🎯 Running evaluation with {len(demo_questions)} demo questions...")
        print()

        # Run the evaluation
        results = await evaluator.run_full_evaluation(demo_questions)

        print()
        print("=" * 60)
        print("📊 EVALUATION RESULTS SUMMARY")
        print("=" * 60)

        metrics = results["metrics"]

        print("
🎯 SUCCESS RATES:"        print(".1f"        print(".1f"        print(".1f"        print()
        print("
⚡ EFFICIENCY:"        print(".2f"        print(".2f"        print(".2f"        print()
        print("
⏱️  EXECUTION TIMES:"        print(".2f"        print(".2f"        print(".2f"        print()

        # Show detailed results
        print("📋 DETAILED RESULTS:")
        print("-" * 40)

        for i, (new, baseline) in enumerate(zip(results["new_results"], results["baseline_results"]), 1):
            print(f"Question {i}:")
            print(f"  New System: {'✅' if new['success'] else '❌'} ({new['attempts']} attempts, {new['execution_time']:.2f}s)")
            print(f"  Baseline:    {'✅' if baseline['success'] else '❌'} ({baseline['attempts']} attempts, {baseline['execution_time']:.2f}s)")
            print()

        # Save results
        filename = evaluator.save_evaluation_results(results, "evaluation_demo_results.json")

        print("💾 Results saved to:", filename)
        print()

        # Show the report
        print("📄 EVALUATION REPORT:")
        print("=" * 60)
        print(results["report"])

        return results

    except Exception as e:
        print(f"❌ Evaluation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def run_quick_comparison():
    """Run a quick comparison to verify the systems work."""

    print("🔍 Quick System Comparison Test")
    print("-" * 40)

    try:
        config = Config()
        llm_manager = LLMManager(config)
        redis_manager = RedisManager(config)
        db_manager = DatabaseManager(config)

        llm = llm_manager.get_client()
        evaluator = RepairLoopEvaluator(llm=llm, db=db_manager, redis_client=redis_manager.client)

        # Test a simple question
        question = "How many crime incidents were reported in 2023?"

        print(f"Testing: {question}")
        print()

        # Test new system
        print("🆕 Testing NEW History-Aware System...")
        new_result = await evaluator.evaluate_single_question(question, use_new_system=True)
        print(f"   Result: {'✅ SUCCESS' if new_result.success else '❌ FAILED'}")
        print(f"   Attempts: {new_result.attempts}")
        print(f"   Time: {new_result.execution_time:.2f}s")
        print(f"   SQL: {new_result.final_sql[:100]}...")
        print()

        # Test baseline
        print("📊 Testing LEGACY Baseline System...")
        baseline_result = await evaluator.evaluate_single_question(question, use_new_system=False)
        print(f"   Result: {'✅ SUCCESS' if baseline_result.success else '❌ FAILED'}")
        print(f"   Attempts: {baseline_result.attempts}")
        print(f"   Time: {baseline_result.execution_time:.2f}s")
        print(f"   SQL: {baseline_result.final_sql[:100]}...")
        print()

        # Compare
        print("⚖️  COMPARISON:")
        if new_result.success and not baseline_result.success:
            print("   🏆 NEW SYSTEM WINS: Baseline failed but new system succeeded")
        elif baseline_result.success and not new_result.success:
            print("   📉 BASELINE WINS: New system failed but baseline succeeded")
        elif new_result.success and baseline_result.success:
            if new_result.attempts < baseline_result.attempts:
                print(f"   🎯 NEW SYSTEM MORE EFFICIENT: {baseline_result.attempts - new_result.attempts} fewer attempts")
            elif new_result.attempts > baseline_result.attempts:
                print(f"   🤔 BASELINE MORE EFFICIENT: {new_result.attempts - baseline_result.attempts} fewer attempts")
            else:
                print("   🤝 EQUAL PERFORMANCE: Both systems used same number of attempts")
        else:
            print("   💥 BOTH SYSTEMS FAILED: Further investigation needed")

    except Exception as e:
        print(f"❌ Quick comparison failed: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Run quick comparison
        asyncio.run(run_quick_comparison())
    else:
        # Run full evaluation demo
        asyncio.run(run_evaluation_demo())