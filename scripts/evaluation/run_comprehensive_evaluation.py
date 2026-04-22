#!/usr/bin/env python3
"""
NORP Repair Loop - Comprehensive Evaluation Runner
Runs full evaluation comparing History-Aware Repair Loop vs Legacy Baseline
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from evaluation_system import RepairLoopEvaluator
from config.config import Config
from services.llm_manager.LLMManager import LLMManager
from services.redis_manager.RedisManager import RedisManager
from services.sql_manager.DatabaseManager import DatabaseManager


class EvaluationRunner:
    """Comprehensive evaluation runner for NORP Repair Loop."""

    def __init__(self):
        self.config = None
        self.llm_manager = None
        self.redis_manager = None
        self.db_manager = None
        self.evaluator = None

    def initialize_components(self):
        """Initialize all required components."""
        print("🔧 Initializing evaluation components...")

        try:
            self.config = Config()
            self.llm_manager = LLMManager(self.config)
            self.redis_manager = RedisManager(self.config)
            self.db_manager = DatabaseManager(self.config)

            # Get the LLM client
            llm = self.llm_manager.get_client()

            # Create evaluator
            self.evaluator = RepairLoopEvaluator(
                llm=llm,
                db=self.db_manager,
                redis_client=self.redis_manager.client
            )

            print("✅ All components initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize components: {str(e)}")
            return False

    async def run_comprehensive_evaluation(self):
        """Run comprehensive evaluation with all test questions."""

        if not self.evaluator:
            print("❌ Evaluator not initialized")
            return None

        # Comprehensive test questions covering different scenarios
        test_questions = [
            # Crime data queries
            "How many crime incidents were reported in 2023?",
            "What are the top 5 crime types in Atlanta?",
            "List all crime incidents that occurred on weekends",

            # Demographic queries
            "Show me demographic data for zip code 30005",
            "Display demographic information for Hispanic population",
            "What is the population distribution by race in Georgia?",

            # Housing queries
            "How many housing units are valued over $500,000?",
            "What is the average rent for housing units in zip code 30004?",
            "Show housing data for areas with more than 1000 units",
            "Find housing units with rent between $1000 and $2000",

            # Complex queries
            "What are the most common crime types by area?",
            "Show me housing value trends by zip code",
            "Compare demographic changes between different zip codes"
        ]

        print(f"🔬 Starting Comprehensive Evaluation")
        print(f"📊 Testing {len(test_questions)} questions")
        print(f"⚡ Comparing History-Aware System vs Legacy Baseline")
        print("=" * 80)

        # Run evaluation
        results = await self.evaluator.run_full_evaluation(test_questions)

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_evaluation_{timestamp}.json"
        self.evaluator.save_evaluation_results(results, filename)

        # Generate summary report
        self._generate_summary_report(results, timestamp)

        return results

    def _generate_summary_report(self, results: dict, timestamp: str):
        """Generate a comprehensive summary report."""

        metrics = results["metrics"]

        report = f"""
# NORP Repair Loop - Comprehensive Evaluation Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Evaluation ID:** {timestamp}

## Executive Summary

This comprehensive evaluation compares the new **History-Aware Repair Loop** system
against a **Legacy Baseline** implementation across {metrics['new_system']['total_questions']} diverse SQL generation tasks.

## Key Findings

### 🎯 Success Rate Improvement
- **New System:** {metrics['new_system']['success_rate']:.1f}%
- **Legacy Baseline:** {metrics['baseline_system']['success_rate']:.1f}%
- **Improvement:** {metrics['improvements']['success_rate_improvement']:+.1f} percentage points

### ⚡ Efficiency Gains
- **Average Attempts (New):** {metrics['new_system']['avg_attempts']:.2f}
- **Average Attempts (Baseline):** {metrics['baseline_system']['avg_attempts']:.2f}
- **Attempts Reduction:** {metrics['improvements']['attempts_reduction']:+.2f} fewer attempts per query

### ⏱️ Performance Metrics
- **Average Execution Time (New):** {metrics['new_system']['avg_execution_time']:.2f}s
- **Average Execution Time (Baseline):** {metrics['baseline_system']['avg_execution_time']:.2f}s
- **Time Improvement:** {metrics['improvements']['time_improvement']:+.2f}s per query

## Detailed Performance Breakdown

### New History-Aware System
- **Total Queries Tested:** {metrics['new_system']['total_questions']}
- **Successful Queries:** {metrics['new_system']['successful_queries']}
- **Success Rate:** {metrics['new_system']['success_rate']:.1f}%
- **Average Attempts (All):** {metrics['new_system']['avg_attempts']:.2f}
- **Average Attempts (Successful Only):** {metrics['new_system']['avg_attempts_successful']:.2f}
- **Average Execution Time (All):** {metrics['new_system']['avg_execution_time']:.2f}s
- **Average Execution Time (Successful Only):** {metrics['new_system']['avg_execution_time_successful']:.2f}s

### Legacy Baseline System
- **Total Queries Tested:** {metrics['baseline_system']['total_questions']}
- **Successful Queries:** {metrics['baseline_system']['successful_queries']}
- **Success Rate:** {metrics['baseline_system']['success_rate']:.1f}%
- **Average Attempts (All):** {metrics['baseline_system']['avg_attempts']:.2f}
- **Average Attempts (Successful Only):** {metrics['baseline_system']['avg_attempts_successful']:.2f}
- **Average Execution Time (All):** {metrics['baseline_system']['avg_execution_time']:.2f}s
- **Average Execution Time (Successful Only):** {metrics['baseline_system']['avg_execution_time_successful']:.2f}s

## Query-by-Query Results

"""

        # Add detailed results
        for i, (new, baseline) in enumerate(zip(results["new_results"], results["baseline_results"]), 1):
            status_new = "✅ SUCCESS" if new['success'] else "❌ FAILED"
            status_baseline = "✅ SUCCESS" if baseline['success'] else "❌ FAILED"

            improvement = ""
            if new['success'] and baseline['success']:
                if new['attempts'] < baseline['attempts']:
                    improvement = f" 🎯 IMPROVED ({baseline['attempts'] - new['attempts']} fewer attempts)"
                elif new['attempts'] > baseline['attempts']:
                    improvement = f" 📉 REGRESSED ({new['attempts'] - baseline['attempts']} more attempts)"
                else:
                    improvement = " 🤝 EQUAL performance"
            elif new['success'] and not baseline['success']:
                improvement = " 🏆 NEW SYSTEM FIXED baseline failure"
            elif not new['success'] and baseline['success']:
                improvement = " 💔 NEW SYSTEM REGRESSED from baseline success"

            report += f"""### Query {i}: {new['question'][:60]}{'...' if len(new['question']) > 60 else ''}

**New System:** {status_new} ({new['attempts']} attempts, {new['execution_time']:.2f}s)
**Baseline:** {status_baseline} ({baseline['attempts']} attempts, {baseline['execution_time']:.2f}s)
**Result:** {improvement}

"""

        # Add conclusion
        conclusion = self._generate_conclusion(metrics)
        report += conclusion

        # Save report
        report_filename = f"evaluation_report_{timestamp}.md"
        with open(report_filename, 'w') as f:
            f.write(report)

        print(f"\n📄 Comprehensive report saved to: {report_filename}")

        # Print summary to console
        print("\n" + "="*80)
        print("🎯 EVALUATION SUMMARY")
        print("="*80)
        print(f"Success Rate Improvement: {metrics['improvements']['success_rate_improvement']:+.1f}%")
        print(f"Attempts Reduction: {metrics['improvements']['attempts_reduction']:+.2f} attempts")
        print(f"Time Improvement: {metrics['improvements']['time_improvement']:+.2f}s")
        print("="*80)

    def _generate_conclusion(self, metrics: dict) -> str:
        """Generate conclusion based on metrics."""

        success_improvement = metrics['improvements']['success_rate_improvement']
        attempts_reduction = metrics['improvements']['attempts_reduction']
        time_improvement = metrics['improvements']['time_improvement']

        conclusion = """

## Conclusion and Recommendations

"""

        if success_improvement > 10 and attempts_reduction > 0.5:
            conclusion += """### 🎉 EXCELLENT RESULTS - Strong Recommendation for Production Deployment

The History-Aware Repair Loop demonstrates **significant improvements** over the legacy baseline:

- **High Success Rate Improvement** (>10 percentage points)
- **Meaningful Efficiency Gains** (reduced refinement attempts)
- **Consistent Performance** across diverse query types

**Recommendation:** ✅ **APPROVE for production deployment**

**Key Benefits:**
- Better user experience with higher success rates
- Reduced computational overhead
- More reliable SQL generation
- Learning from past mistakes prevents repeated errors

"""
        elif success_improvement > 5 or attempts_reduction > 0.2:
            conclusion += """### 👍 GOOD RESULTS - Recommended with Monitoring

The History-Aware Repair Loop shows **moderate improvements** over the legacy baseline:

- **Noticeable Success Rate Improvement** (>5 percentage points)
- **Some Efficiency Gains** (reduced refinement attempts)
- **Stable Performance** across most query types

**Recommendation:** ✅ **APPROVE for production with monitoring**

**Next Steps:**
- Deploy with performance monitoring
- Collect user feedback
- Consider further optimizations for edge cases

"""
        elif success_improvement >= 0:
            conclusion += """### 🤔 NEUTRAL RESULTS - Further Investigation Needed

The History-Aware Repair Loop shows **minimal or no improvement** over the legacy baseline:

- **Limited Success Rate Improvement** (≤5 percentage points)
- **Minimal Efficiency Changes**
- **Mixed Performance** across query types

**Recommendation:** 🔄 **REQUIRES FURTHER INVESTIGATION**

**Suggested Actions:**
- Analyze failure cases in detail
- Review history tracking implementation
- Test with different query patterns
- Consider alternative approaches

"""
        else:
            conclusion += """### ⚠️ CONCERNING RESULTS - Not Recommended for Production

The History-Aware Repair Loop shows **regression** compared to the legacy baseline:

- **Lower Success Rate** than baseline
- **Potential Efficiency Issues**
- **Performance Degradation**

**Recommendation:** ❌ **DO NOT DEPLOY**

**Required Actions:**
- Debug history tracking implementation
- Review prompt engineering
- Test with simpler baseline comparisons
- Re-evaluate the approach

"""

        conclusion += f"""
## Technical Summary

- **Evaluation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Test Queries:** {metrics['new_system']['total_questions']}
- **New System Success Rate:** {metrics['new_system']['success_rate']:.1f}%
- **Baseline Success Rate:** {metrics['baseline_system']['success_rate']:.1f}%
- **Average Improvement:** {success_improvement:.1f} percentage points

## Files Generated
- `comprehensive_evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json` - Detailed results
- `evaluation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md` - This report
"""

        return conclusion


async def main():
    """Main evaluation runner."""

    print("🔬 NORP Repair Loop - Comprehensive Evaluation System")
    print("=" * 80)

    runner = EvaluationRunner()

    if not runner.initialize_components():
        print("❌ Evaluation aborted due to initialization failure")
        return 1

    try:
        results = await runner.run_comprehensive_evaluation()

        if results:
            print("✅ Evaluation completed successfully!")
            print("📊 Check the generated report files for detailed analysis")
            return 0
        else:
            print("❌ Evaluation failed")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Evaluation failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)