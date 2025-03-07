#!/usr/bin/env python3
"""
Compare evaluation results between RAG and non-RAG runs.
"""

import os
import sys
import json
import argparse
import pandas as pd
from tabulate import tabulate

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Compare evaluation results between RAG and non-RAG runs")
    parser.add_argument("--no-rag", type=str, required=True, help="Path to no-RAG evaluation JSON results")
    parser.add_argument("--rag", type=str, required=True, help="Path to RAG evaluation JSON results")
    parser.add_argument("--output", type=str, help="Path to output CSV file for comparison")
    return parser.parse_args()

def load_results(filepath):
    """Load evaluation results from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def compare_metrics(metrics1, metrics2):
    """Compare metrics between two evaluation runs"""
    comparison = {}
    
    # Get all unique metric keys
    all_keys = set(metrics1.keys()) | set(metrics2.keys())
    
    # Compare each metric
    for key in all_keys:
        val1 = metrics1.get(key, 0)
        val2 = metrics2.get(key, 0)
        
        # For percentage metrics, calculate absolute difference
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            diff = val2 - val1
            diff_str = f"{diff:+.2f}" if isinstance(diff, float) else f"{diff:+d}"
            comparison[key] = {
                "no_rag": val1,
                "rag": val2,
                "diff": diff,
                "diff_str": diff_str
            }
        else:
            comparison[key] = {
                "no_rag": val1,
                "rag": val2,
                "diff": "N/A",
                "diff_str": "N/A"
            }
    
    return comparison

def format_comparison_table(comparison):
    """Format comparison results as a table"""
    table_data = []
    
    for metric, values in comparison.items():
        no_rag_val = values["no_rag"]
        rag_val = values["rag"]
        diff_str = values["diff_str"]
        
        # Format percentages
        if isinstance(no_rag_val, float) and isinstance(rag_val, float):
            no_rag_str = f"{no_rag_val:.2f}%"
            rag_str = f"{rag_val:.2f}%"
            if values["diff"] > 0:
                diff_display = f"+{values['diff']:.2f}% 🔼"
            elif values["diff"] < 0:
                diff_display = f"{values['diff']:.2f}% 🔽"
            else:
                diff_display = "0.00% ⟹"
        else:
            no_rag_str = str(no_rag_val)
            rag_str = str(rag_val)
            diff_display = diff_str
        
        table_data.append([metric, no_rag_str, rag_str, diff_display])
    
    return tabulate(
        table_data,
        headers=["Metric", "No RAG", "With RAG", "Difference"],
        tablefmt="grid"
    )

def create_detailed_comparison(results1, results2):
    """Create detailed comparison of query results"""
    df1 = pd.DataFrame(results1["results"])
    df2 = pd.DataFrame(results2["results"])
    
    # Merge dataframes on natural language query
    merged = pd.merge(
        df1, df2, 
        on="nl_query", 
        suffixes=("_no_rag", "_rag")
    )
    
    # Add comparison columns
    merged["syntax_improved"] = merged["syntactically_correct_rag"] & ~merged["syntactically_correct_no_rag"]
    merged["syntax_worsened"] = ~merged["syntactically_correct_rag"] & merged["syntactically_correct_no_rag"]
    merged["logic_improved"] = merged["logically_correct_rag"] & ~merged["logically_correct_no_rag"]
    merged["logic_worsened"] = ~merged["logically_correct_rag"] & merged["logically_correct_no_rag"]
    
    return merged

def main():
    """Main function"""
    args = parse_args()
    
    # Load evaluation results
    no_rag_results = load_results(args.no_rag)
    rag_results = load_results(args.rag)
    
    if not no_rag_results or not rag_results:
        print("Failed to load one or both result files")
        return 1
    
    # Compare metrics
    metrics_comparison = compare_metrics(no_rag_results["metrics"], rag_results["metrics"])
    
    # Print comparison table
    print("\n=== METRICS COMPARISON ===")
    print(format_comparison_table(metrics_comparison))
    
    # Create detailed comparison
    try:
        detailed_comparison = create_detailed_comparison(no_rag_results, rag_results)
        
        # Print summary of improvements
        syntax_improved = detailed_comparison["syntax_improved"].sum()
        syntax_worsened = detailed_comparison["syntax_worsened"].sum()
        logic_improved = detailed_comparison["logic_improved"].sum()
        logic_worsened = detailed_comparison["logic_worsened"].sum()
        
        print("\n=== DETAILED COMPARISON ===")
        print(f"Total queries: {len(detailed_comparison)}")
        print(f"Syntax improved (No RAG → RAG): {syntax_improved} queries")
        print(f"Syntax worsened (No RAG → RAG): {syntax_worsened} queries")
        print(f"Logic improved (No RAG → RAG): {logic_improved} queries")
        print(f"Logic worsened (No RAG → RAG): {logic_worsened} queries")
        
        # Save detailed comparison to CSV if requested
        if args.output:
            detailed_comparison.to_csv(args.output, index=False)
            print(f"\nDetailed comparison saved to {args.output}")
    
    except Exception as e:
        print(f"Error creating detailed comparison: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 