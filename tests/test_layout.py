"""
Unit tests for layout parsing and aggregation functions.
"""

import unittest
import pandas as pd
from calc.layout import (
    parse_layout,
    make_hall_names,
    column_aggregates,
    create_hall_dataframe,
    validate_hall_data,
    get_layout_stats
)


class TestLayoutParsing(unittest.TestCase):
    """Test layout parsing functionality."""
    
    def test_parse_layout_valid_formats(self):
        """Test parsing of valid layout strings."""
        # Standard format with ×
        columns, rows, floors = parse_layout("4×3×2")
        self.assertEqual((columns, rows, floors), (4, 3, 2))
        
        # Format with x
        columns, rows, floors = parse_layout("4x3x2")
        self.assertEqual((columns, rows, floors), (4, 3, 2))
        
        # Single digit
        columns, rows, floors = parse_layout("1x1x1")
        self.assertEqual((columns, rows, floors), (1, 1, 1))
        
        # Large numbers
        columns, rows, floors = parse_layout("10x15x5")
        self.assertEqual((columns, rows, floors), (10, 15, 5))
    
    def test_parse_layout_with_spaces(self):
        """Test parsing with extra whitespace."""
        columns, rows, floors = parse_layout("  4 x 3 x 2  ")
        self.assertEqual((columns, rows, floors), (4, 3, 2))
    
    def test_parse_layout_invalid_formats(self):
        """Test parsing of invalid layout strings."""
        invalid_formats = [
            "",
            "4x3",  # Missing floors
            "4x3x2x1",  # Too many dimensions
            "axbxc",  # Non-numeric
            "4x-3x2",  # Negative numbers
            "4x0x2",  # Zero dimensions
            "4.5x3x2",  # Decimal numbers
        ]
        
        for fmt in invalid_formats:
            with self.assertRaises(ValueError):
                parse_layout(fmt)
    
    def test_parse_layout_none_and_empty(self):
        """Test parsing with None and empty inputs."""
        with self.assertRaises(ValueError):
            parse_layout(None)
        
        with self.assertRaises(ValueError):
            parse_layout("")


class TestHallNames(unittest.TestCase):
    """Test hall name generation."""
    
    def test_make_hall_names_simple(self):
        """Test basic hall name generation."""
        names = make_hall_names(2, 2, 1, include_floors=False)
        expected = ["A1", "A2", "B1", "B2"]
        self.assertEqual(names, expected)
    
    def test_make_hall_names_with_floors(self):
        """Test hall names with floor numbers."""
        names = make_hall_names(2, 2, 2, include_floors=True)
        expected = [
            "A1-F1", "A2-F1", "B1-F1", "B2-F1",
            "A1-F2", "A2-F2", "B1-F2", "B2-F2"
        ]
        self.assertEqual(names, expected)
    
    def test_make_hall_names_many_columns(self):
        """Test hall names with many columns (>26)."""
        names = make_hall_names(28, 1, 1, include_floors=False)
        # Should go A, B, ..., Z, AA, AB
        self.assertEqual(names[0], "A1")
        self.assertEqual(names[25], "Z1")
        self.assertEqual(names[26], "AA1")
        self.assertEqual(names[27], "AB1")
    
    def test_make_hall_names_edge_cases(self):
        """Test edge cases."""
        # Single hall
        names = make_hall_names(1, 1, 1, include_floors=False)
        self.assertEqual(names, ["A1"])
        
        # Multiple floors, single hall per floor
        names = make_hall_names(1, 1, 3, include_floors=True)
        self.assertEqual(names, ["A1-F1", "A1-F2", "A1-F3"])


class TestColumnAggregates(unittest.TestCase):
    """Test column aggregation functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_hall_data = pd.DataFrame({
            'Hall': ['A1-F1', 'A2-F1', 'B1-F1', 'B2-F1', 'A1-F2', 'B1-F2'],
            'IT Load (MW)': [5.0, 3.0, 4.0, 2.0, 5.0, 4.0]
        })
    
    def test_column_aggregates_basic(self):
        """Test basic column aggregation."""
        result = column_aggregates(self.sample_hall_data, 2, 2, 2, include_floors=True)
        
        # Check structure
        expected_columns = ['Column', 'Total_MW', 'Hall_Count', 'Halls']
        self.assertEqual(list(result.columns), expected_columns)
        
        # Check values
        self.assertEqual(len(result), 2)  # Should have columns A and B
        
        # Column A should have 13 MW total (5+3+5)
        col_a = result[result['Column'] == 'A']
        self.assertEqual(col_a['Total_MW'].iloc[0], 13.0)
        self.assertEqual(col_a['Hall_Count'].iloc[0], 3)
        
        # Column B should have 10 MW total (4+2+4)
        col_b = result[result['Column'] == 'B']
        self.assertEqual(col_b['Total_MW'].iloc[0], 10.0)
        self.assertEqual(col_b['Hall_Count'].iloc[0], 3)
    
    def test_column_aggregates_empty_data(self):
        """Test aggregation with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['Hall', 'IT Load (MW)'])
        result = column_aggregates(empty_df, 2, 2, 1, include_floors=False)
        
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ['Column', 'Total_MW', 'Hall_Count', 'Halls'])
    
    def test_column_aggregates_single_column(self):
        """Test aggregation with single column."""
        single_col_data = pd.DataFrame({
            'Hall': ['A1', 'A2', 'A3'],
            'IT Load (MW)': [2.0, 3.0, 5.0]
        })
        
        result = column_aggregates(single_col_data, 1, 3, 1, include_floors=False)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result['Column'].iloc[0], 'A')
        self.assertEqual(result['Total_MW'].iloc[0], 10.0)
        self.assertEqual(result['Hall_Count'].iloc[0], 3)


class TestCreateHallDataFrame(unittest.TestCase):
    """Test hall DataFrame creation."""
    
    def test_create_hall_dataframe_basic(self):
        """Test basic DataFrame creation."""
        df = create_hall_dataframe("2x2x1", include_floors=False, default_mw=1.5)
        
        expected_halls = ['A1', 'A2', 'B1', 'B2']
        self.assertEqual(list(df['Hall']), expected_halls)
        self.assertEqual(list(df['IT Load (MW)']), [1.5, 1.5, 1.5, 1.5])
    
    def test_create_hall_dataframe_with_floors(self):
        """Test DataFrame creation with floors."""
        df = create_hall_dataframe("2x2x2", include_floors=True, default_mw=2.0)
        
        expected_count = 8  # 2x2x2
        self.assertEqual(len(df), expected_count)
        self.assertTrue(all(df['IT Load (MW)'] == 2.0))
        self.assertTrue(all('-F' in hall for hall in df['Hall']))
    
    def test_create_hall_dataframe_invalid_layout(self):
        """Test DataFrame creation with invalid layout."""
        df = create_hall_dataframe("invalid", include_floors=False, default_mw=1.0)
        
        # Should return empty DataFrame
        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), ['Hall', 'IT Load (MW)'])


class TestValidateHallData(unittest.TestCase):
    """Test hall data validation."""
    
    def test_validate_hall_data_valid(self):
        """Test validation of valid data."""
        valid_df = pd.DataFrame({
            'Hall': ['A1', 'A2', 'B1'],
            'IT Load (MW)': [1.0, 2.0, 3.0]
        })
        
        is_valid, error_msg = validate_hall_data(valid_df)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_hall_data_empty(self):
        """Test validation of empty data."""
        empty_df = pd.DataFrame()
        
        is_valid, error_msg = validate_hall_data(empty_df)
        self.assertFalse(is_valid)
        self.assertIn("empty", error_msg.lower())
    
    def test_validate_hall_data_missing_columns(self):
        """Test validation with missing columns."""
        missing_col_df = pd.DataFrame({
            'Hall': ['A1', 'A2'],
            # Missing 'IT Load (MW)' column
        })
        
        is_valid, error_msg = validate_hall_data(missing_col_df)
        self.assertFalse(is_valid)
        self.assertIn("Missing required columns", error_msg)
    
    def test_validate_hall_data_negative_mw(self):
        """Test validation with negative MW values."""
        negative_df = pd.DataFrame({
            'Hall': ['A1', 'A2'],
            'IT Load (MW)': [1.0, -2.0]
        })
        
        is_valid, error_msg = validate_hall_data(negative_df)
        self.assertFalse(is_valid)
        self.assertIn("non-negative", error_msg)
    
    def test_validate_hall_data_empty_hall_names(self):
        """Test validation with empty hall names."""
        empty_names_df = pd.DataFrame({
            'Hall': ['A1', ''],
            'IT Load (MW)': [1.0, 2.0]
        })
        
        is_valid, error_msg = validate_hall_data(empty_names_df)
        self.assertFalse(is_valid)
        self.assertIn("valid names", error_msg)


class TestGetLayoutStats(unittest.TestCase):
    """Test layout statistics function."""
    
    def test_get_layout_stats_valid(self):
        """Test statistics for valid layout."""
        stats = get_layout_stats("4x3x2", include_floors=True)
        
        self.assertTrue(stats['valid'])
        self.assertIsNone(stats['error'])
        self.assertEqual(stats['columns'], 4)
        self.assertEqual(stats['rows'], 3)
        self.assertEqual(stats['floors'], 2)
        self.assertEqual(stats['total_halls'], 24)  # 4*3*2
        self.assertEqual(stats['halls_per_floor'], 12)  # 4*3
    
    def test_get_layout_stats_invalid(self):
        """Test statistics for invalid layout."""
        stats = get_layout_stats("invalid_format", include_floors=True)
        
        self.assertFalse(stats['valid'])
        self.assertIsNotNone(stats['error'])
        self.assertEqual(stats['columns'], 0)
        self.assertEqual(stats['total_halls'], 0)


if __name__ == '__main__':
    unittest.main()