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
    get_layout_stats,
    calculate_riser_count,
    build_hall_table,
    calculate_riser_reduction_schedule,
    get_column_summary
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


class TestEnhancedFeatures(unittest.TestCase):
    """Test enhanced V2 features."""
    
    def test_calculate_riser_count(self):
        """Test riser count calculations."""
        # Test shared risers: 2*(C+R)
        shared_count = calculate_riser_count(4, 3, True)
        self.assertEqual(shared_count, 2 * (4 + 3))  # 14
        
        # Test unshared risers: 4*(C+R)
        unshared_count = calculate_riser_count(4, 3, False)
        self.assertEqual(unshared_count, 4 * (4 + 3))  # 28
        
        # Edge case: minimal layout
        minimal_shared = calculate_riser_count(1, 1, True)
        self.assertEqual(minimal_shared, 4)  # 2*(1+1)
    
    def test_build_hall_table(self):
        """Test comprehensive hall table building."""
        it_data = {
            'A1-F1': 2.0,
            'A1-F2': 2.0, 
            'B1-F1': 1.5,
            'B1-F2': 1.5
        }
        
        hall_table = build_hall_table(
            columns=2, rows=1, floors=2,
            it_mw_data=it_data,
            fan_percent=5.0,
            misc_load_mw=1.0,
            misc_per_hall=True
        )
        
        # Check structure
        expected_columns = ['Hall', 'Column', 'Row', 'Floor', 'IT_MW', 'Fan_MW', 'Misc_MW', 'Total_Cooling_MW']
        self.assertEqual(list(hall_table.columns), expected_columns)
        self.assertEqual(len(hall_table), 4)
        
        # Check calculations
        for _, row in hall_table.iterrows():
            expected_fan = row['IT_MW'] * 0.05  # 5%
            expected_misc = 1.0 / 4  # 1MW divided by 4 halls
            expected_total = row['IT_MW'] + expected_fan + expected_misc
            
            self.assertAlmostEqual(row['Fan_MW'], expected_fan, places=2)
            self.assertAlmostEqual(row['Misc_MW'], expected_misc, places=2)
            self.assertAlmostEqual(row['Total_Cooling_MW'], expected_total, places=2)
    
    def test_calculate_riser_reduction_schedule(self):
        """Test per-floor reduction schedule calculation."""
        # Create test hall table
        hall_data = [
            {'Hall': 'A1-F1', 'Column': 'A', 'Floor': 1, 'Total_Cooling_MW': 2.0},
            {'Hall': 'A1-F2', 'Column': 'A', 'Floor': 2, 'Total_Cooling_MW': 1.5},
            {'Hall': 'B1-F1', 'Column': 'B', 'Floor': 1, 'Total_Cooling_MW': 1.0},
            {'Hall': 'B1-F2', 'Column': 'B', 'Floor': 2, 'Total_Cooling_MW': 0.8}
        ]
        hall_table = pd.DataFrame(hall_data)
        
        reduction_schedule = calculate_riser_reduction_schedule(hall_table, 2, 1, 2)
        
        # Should have entries for each column and floor
        self.assertGreaterEqual(len(reduction_schedule), 4)
        
        # Check column structure  
        expected_cols = ['Column', 'Floor', 'Floor_Load_MW', 'Cumulative_Load_MW', 'Remaining_Load_MW']
        self.assertEqual(list(reduction_schedule.columns), expected_cols)
        
        # Check that remaining load increases as we go down floors (lower floors carry more load)
        for column in ['A', 'B']:
            col_data = reduction_schedule[reduction_schedule['Column'] == column].sort_values('Floor')
            if len(col_data) > 1:
                # Lower floor (floor 1) should have less remaining load than higher floor (floor 2)
                # because remaining load = load that still needs to be carried by the riser at that level
                self.assertLessEqual(col_data.iloc[0]['Remaining_Load_MW'], col_data.iloc[-1]['Remaining_Load_MW'])
    
    def test_get_column_summary(self):
        """Test column summary aggregation."""
        hall_data = [
            {'Column': 'A', 'IT_MW': 2.0, 'Fan_MW': 0.1, 'Misc_MW': 0.2, 'Total_Cooling_MW': 2.3, 'Hall': 'A1-F1'},
            {'Column': 'A', 'IT_MW': 1.5, 'Fan_MW': 0.08, 'Misc_MW': 0.2, 'Total_Cooling_MW': 1.78, 'Hall': 'A1-F2'},
            {'Column': 'B', 'IT_MW': 1.0, 'Fan_MW': 0.05, 'Misc_MW': 0.2, 'Total_Cooling_MW': 1.25, 'Hall': 'B1-F1'}
        ]
        hall_table = pd.DataFrame(hall_data)
        
        summary = get_column_summary(hall_table)
        
        # Check structure
        expected_cols = ['Column', 'Total_IT_MW', 'Total_Fan_MW', 'Total_Misc_MW', 'Total_Cooling_MW', 'Hall_Count']
        self.assertEqual(list(summary.columns), expected_cols)
        
        # Check values
        col_a = summary[summary['Column'] == 'A'].iloc[0]
        self.assertAlmostEqual(col_a['Total_IT_MW'], 3.5, places=1)  # 2.0 + 1.5
        self.assertEqual(col_a['Hall_Count'], 2)
        
        col_b = summary[summary['Column'] == 'B'].iloc[0]
        self.assertAlmostEqual(col_b['Total_IT_MW'], 1.0, places=1)
        self.assertEqual(col_b['Hall_Count'], 1)


if __name__ == '__main__':
    unittest.main()