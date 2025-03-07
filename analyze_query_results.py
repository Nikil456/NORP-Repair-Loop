import pandas as pd
import re
import argparse
from collections import Counter

def analyze_results(csv_file):
    """Analyze the query test results CSV file"""
    # Load the results
    df = pd.read_csv(csv_file)
    
    # Basic statistics
    total_queries = len(df)
    successful = df[df['success'] == True]
    failed = df[df['success'] == False]
    success_count = len(successful)
    failure_count = len(failed)
    success_rate = (success_count / total_queries) * 100 if total_queries > 0 else 0
    
    print(f"Total Queries: {total_queries}")
    print(f"Successful Queries: {success_count} ({success_rate:.2f}%)")
    print(f"Failed Queries: {failure_count} ({100-success_rate:.2f}%)")
    
    # Analyze failure reasons
    if failure_count > 0:
        print("\n== Failure Analysis ==")
        
        # Group by error message
        error_counts = Counter(failed['message'])
        print(f"\nTop 10 Error Messages:")
        for error, count in error_counts.most_common(10):
            print(f"  - {count} queries failed with: {error[:100]}{'...' if len(error) > 100 else ''}")
        
        # Find missing tables
        missing_tables_pattern = r"Tables not found in database: \[(.*?)\]"
        missing_tables = []
        for error in failed['message']:
            if isinstance(error, str):
                match = re.search(missing_tables_pattern, error)
                if match:
                    tables_str = match.group(1)
                    tables = [t.strip().strip("'") for t in tables_str.split(",")]
                    missing_tables.extend(tables)
        
        if missing_tables:
            print("\nMissing Tables (by frequency):")
            for table, count in Counter(missing_tables).most_common():
                print(f"  - '{table}': {count} queries")
        
        # Analyze syntax errors
        syntax_errors = failed[failed['message'].str.contains('syntax', case=False, na=False)]
        if len(syntax_errors) > 0:
            print(f"\nSyntax Errors: {len(syntax_errors)} queries")
            # Extract common syntax error patterns
            error_patterns = []
            for error in syntax_errors['message']:
                if 'near' in error:
                    pattern = re.search(r"near ['\"](.+?)['\"]", error)
                    if pattern:
                        error_patterns.append(pattern.group(1))
            
            if error_patterns:
                print("Common syntax error patterns:")
                for pattern, count in Counter(error_patterns).most_common(5):
                    print(f"  - '{pattern}': {count} queries")
    
    # Analyze successful queries
    if success_count > 0:
        print("\n== Success Analysis ==")
        
        # Analyze which tables are used in successful queries
        tables_in_successful = []
        for tables_list in successful['tables']:
            if isinstance(tables_list, str):
                tables = eval(tables_list)
                tables_in_successful.extend(tables)
        
        if tables_in_successful:
            print("\nMost Used Tables in Successful Queries:")
            for table, count in Counter(tables_in_successful).most_common():
                print(f"  - '{table}': {count} queries")
    
    return {
        'total': total_queries,
        'success': success_count,
        'failure': failure_count,
        'success_rate': success_rate
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze SQL query test results')
    parser.add_argument('--csv', default='query_test_results.csv', help='Path to results CSV file')
    args = parser.parse_args()
    
    analyze_results(args.csv)

if __name__ == "__main__":
    main() 