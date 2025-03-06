"""
Utility.py has all the basic utility methods required by app.
"""
from decimal import Decimal

def read_gpg_encrypted_file(file_path):
    """Reads key from encrypted."""
    with open(file_path, 'r') as fp:
        key = fp.read() 
    return key

def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, list):
        return [decimal_to_float(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(decimal_to_float(item) for item in value)
    elif isinstance(value, dict):
        return {key: decimal_to_float(val) for key, val in value.items()}
    return value

from prettytable import PrettyTable

def pretty_print_results(results, column_names=None):
    """
    Nicely formats and prints SQL query results.

    Args:
        results (list): Query results as a list of dictionaries or tuples.
        column_names (list, optional): Column names for tuple-based results.
                                        If `results` is a list of dictionaries, this can be omitted.
    
    Returns:
        str: Formatted table as a string.
    """
    if not results:
        return "No results to display."

    # Determine columns and rows
    if isinstance(results[0], dict):
        # Extract columns from dictionary keys
        columns = results[0].keys()
        rows = [list(row.values()) for row in results]
    elif column_names:
        # Use provided column names
        columns = column_names
        rows = results
    else:
        return "Error: Column names are required for tuple-based results."

    # Format results using PrettyTable
    table = PrettyTable()
    table.field_names = columns
    for row in rows:
        table.add_row(row)

    return table.get_string()
