"""
Tests for column name utilities to ensure consistent processing.
"""
import sys
import os
import unittest
import pandas as pd

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.column_utils import clean_column_name, clean_dataframe_columns, clean_column_dict


class TestColumnUtils(unittest.TestCase):
    """Test column utilities to ensure consistent preprocessing."""
    
    def test_clean_column_name(self):
        """Test the clean_column_name function."""
        self.assertEqual(clean_column_name("column name"), "column_name")
        self.assertEqual(clean_column_name("column-name"), "column_name")
        self.assertEqual(clean_column_name("column#name"), "column_Numbername")
        self.assertEqual(clean_column_name("column&name"), "columnAndname")
        self.assertEqual(clean_column_name("column%name"), "columnPercentname")
        self.assertEqual(clean_column_name("column(name)"), "columnname")
        self.assertEqual(clean_column_name("column.name"), "columnname")
        self.assertEqual(clean_column_name(123), "123")  # Test non-string input
    
    def test_clean_dataframe_columns(self):
        """Test the clean_dataframe_columns function."""
        df = pd.DataFrame(columns=["column name", "column-name", "column#name", 
                                  "column&name", "column%name", "column(name)", "column.name"])
        cleaned_df = clean_dataframe_columns(df)
        expected_columns = ["column_name", "column_name", "column_Numbername", 
                           "columnAndname", "columnPercentname", "columnname", "columnname"]
        self.assertEqual(list(cleaned_df.columns), expected_columns)
    
    def test_clean_column_dict(self):
        """Test the clean_column_dict function."""
        test_dict = {
            "column name": 1,
            "column-name": 2,
            "column#name": 3,
            "column&name": 4,
            "column%name": 5,
            "column(name)": 6,
            "column.name": 7
        }
        cleaned_dict = clean_column_dict(test_dict)
        expected_dict = {
            "column_name": 1,
            "column_name": 2,  # Note: This will overwrite the previous due to identical keys
            "column_Numbername": 3,
            "columnAndname": 4, 
            "columnPercentname": 5,
            "columnname": 6,
            "columnname": 7   # Note: This will overwrite the previous due to identical keys
        }
        # Adjusted test to account for key overwriting
        self.assertEqual(len(cleaned_dict), 5)  # 5 unique keys after cleaning
        self.assertEqual(cleaned_dict["column_name"], 2)  # Last value wins
        self.assertEqual(cleaned_dict["column_Numbername"], 3)
        self.assertEqual(cleaned_dict["columnAndname"], 4)
        self.assertEqual(cleaned_dict["columnPercentname"], 5)
        self.assertEqual(cleaned_dict["columnname"], 7)  # Last value wins


if __name__ == "__main__":
    unittest.main() 