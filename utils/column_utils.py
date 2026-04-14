"""
Utility functions for column name processing to ensure consistency across the project.
"""

def clean_column_name(column_name):
    """Clean a single column name to match SQL schema format.
    This can be used when processing individual column names.
    
    Args:
        column_name: The column name to clean
        
    Returns:
        str: The cleaned column name
    """
    if not isinstance(column_name, str):
        column_name = str(column_name)
        
    # Apply the standard transformations
    column_name = column_name.replace('#', '_Number')
    column_name = column_name.replace(' ', '_')
    column_name = column_name.replace('-', '_')
    column_name = column_name.replace('&', 'And')
    column_name = column_name.replace('%', 'Percent')
    column_name = column_name.replace('(', '')
    column_name = column_name.replace(')', '')
    column_name = column_name.replace('.', '')
    
    return column_name


def clean_dataframe_columns(df):
    """Clean all column names in a pandas DataFrame to match SQL schema format.
    
    Args:
        df: pandas DataFrame whose columns need to be cleaned
        
    Returns:
        pandas.DataFrame: DataFrame with cleaned column names
    """
    df.columns = [clean_column_name(col) for col in df.columns]
    return df


def clean_column_dict(column_dict):
    """Clean keys in a dictionary where keys are column names.
    
    Args:
        column_dict: Dictionary with column names as keys
        
    Returns:
        dict: Dictionary with cleaned column names as keys
    """
    return {clean_column_name(k): v for k, v in column_dict.items()} 