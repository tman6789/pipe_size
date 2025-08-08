"""
Layout parsing and analysis module for data center floor layouts.

Handles parsing of C×R×F format (Columns × Rows × Floors) layouts,
generates hall names, and performs column-based aggregations for riser sizing.
"""

import pandas as pd
from typing import Tuple, List, Dict, Optional


def parse_layout(layout_str: str) -> Tuple[int, int, int]:
    """
    Parse layout string in format 'C×R×F' or 'CxRxF'.
    
    Args:
        layout_str: Layout specification like '4×3×2' or '4x3x2'
    
    Returns:
        Tuple of (columns, rows, floors)
    
    Raises:
        ValueError: If format is invalid or values are not positive integers
    """
    if not layout_str or not isinstance(layout_str, str):
        raise ValueError("Layout string cannot be empty")
    
    # Replace × with x for consistency
    layout_str = layout_str.replace('×', 'x').strip()
    
    try:
        parts = layout_str.split('x')
        if len(parts) != 3:
            raise ValueError("Layout must be in format 'CxRxF' (columns x rows x floors)")
        
        columns, rows, floors = [int(part.strip()) for part in parts]
        
        if columns <= 0 or rows <= 0 or floors <= 0:
            raise ValueError("All layout dimensions must be positive integers")
        
        return columns, rows, floors
    
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid layout format '{layout_str}': {e}")


def make_hall_names(columns: int, rows: int, floors: int, include_floors: bool = True) -> List[str]:
    """
    Generate hall names based on layout dimensions.
    
    Args:
        columns: Number of columns
        rows: Number of rows
        floors: Number of floors
        include_floors: Whether to include floor numbers in names
    
    Returns:
        List of hall names (e.g., ['A1-F1', 'A2-F1', ..., 'B1-F2', ...])
    """
    hall_names = []
    
    # Column letters: A, B, C, ..., Z, AA, BB, etc.
    col_letters = []
    for i in range(columns):
        if i < 26:
            col_letters.append(chr(ord('A') + i))
        else:
            # For more than 26 columns, use AA, AB, AC...
            first_letter = chr(ord('A') + (i // 26) - 1)
            second_letter = chr(ord('A') + (i % 26))
            col_letters.append(first_letter + second_letter)
    
    # Generate names
    for floor in range(1, floors + 1):
        for col_idx in range(columns):
            for row in range(1, rows + 1):
                if include_floors:
                    hall_name = f"{col_letters[col_idx]}{row}-F{floor}"
                else:
                    hall_name = f"{col_letters[col_idx]}{row}"
                hall_names.append(hall_name)
    
    return hall_names


def column_aggregates(hall_data: pd.DataFrame, columns: int, rows: int, floors: int, 
                     include_floors: bool = True) -> pd.DataFrame:
    """
    Aggregate hall loads by column for riser sizing.
    
    Args:
        hall_data: DataFrame with 'Hall' and 'IT Load (MW)' columns
        columns: Number of columns in layout
        rows: Number of rows in layout  
        floors: Number of floors in layout
        include_floors: Whether hall names include floor numbers
    
    Returns:
        DataFrame with columns: ['Column', 'Total_MW', 'Hall_Count', 'Halls']
    """
    if hall_data.empty:
        return pd.DataFrame(columns=['Column', 'Total_MW', 'Hall_Count', 'Halls'])
    
    # Extract column information from hall names
    hall_data = hall_data.copy()
    
    def extract_column(hall_name: str) -> str:
        """Extract column letter(s) from hall name like 'A1-F2' or 'A1'."""
        if not isinstance(hall_name, str):
            return 'Unknown'
        
        # Handle floor format: A1-F2 -> A1 -> A
        if '-F' in hall_name:
            base_name = hall_name.split('-F')[0]
        else:
            base_name = hall_name
        
        # Extract column letter(s): A1 -> A, AA1 -> AA
        column = ''
        for char in base_name:
            if char.isalpha():
                column += char
            else:
                break
        
        return column if column else 'Unknown'
    
    hall_data['Column'] = hall_data['Hall'].apply(extract_column)
    
    # Aggregate by column
    column_summary = hall_data.groupby('Column').agg({
        'IT Load (MW)': 'sum',
        'Hall': ['count', list]
    }).reset_index()
    
    # Flatten column names
    column_summary.columns = ['Column', 'Total_MW', 'Hall_Count', 'Halls']
    
    # Convert hall lists to readable strings
    column_summary['Halls'] = column_summary['Halls'].apply(
        lambda halls: ', '.join(sorted(halls))
    )
    
    # Sort by column name
    column_summary = column_summary.sort_values('Column').reset_index(drop=True)
    
    return column_summary


def create_hall_dataframe(layout_str: str, include_floors: bool = True, 
                         default_mw: float = 1.0) -> pd.DataFrame:
    """
    Create a DataFrame with hall names and default MW values for user editing.
    
    Args:
        layout_str: Layout specification like '4×3×2'
        include_floors: Whether to include floor numbers in hall names
        default_mw: Default MW value for each hall
    
    Returns:
        DataFrame with 'Hall' and 'IT Load (MW)' columns
    """
    try:
        columns, rows, floors = parse_layout(layout_str)
        hall_names = make_hall_names(columns, rows, floors, include_floors)
        
        df = pd.DataFrame({
            'Hall': hall_names,
            'IT Load (MW)': [default_mw] * len(hall_names)
        })
        
        return df
    
    except ValueError:
        # Return empty DataFrame if layout is invalid
        return pd.DataFrame(columns=['Hall', 'IT Load (MW)'])


def validate_hall_data(hall_data: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate hall data DataFrame.
    
    Args:
        hall_data: DataFrame with hall information
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if hall_data.empty:
        return False, "Hall data is empty"
    
    required_columns = ['Hall', 'IT Load (MW)']
    missing_cols = [col for col in required_columns if col not in hall_data.columns]
    if missing_cols:
        return False, f"Missing required columns: {missing_cols}"
    
    # Check for non-negative MW values
    if (hall_data['IT Load (MW)'] < 0).any():
        return False, "All IT Load values must be non-negative"
    
    # Check for valid hall names
    if hall_data['Hall'].isnull().any() or (hall_data['Hall'] == '').any():
        return False, "All halls must have valid names"
    
    return True, ""


def get_layout_stats(layout_str: str, include_floors: bool = True) -> Dict[str, any]:
    """
    Get statistics about a layout configuration.
    
    Args:
        layout_str: Layout specification like '4×3×2'
        include_floors: Whether floors are included in the layout
    
    Returns:
        Dictionary with layout statistics
    """
    try:
        columns, rows, floors = parse_layout(layout_str)
        hall_names = make_hall_names(columns, rows, floors, include_floors)
        
        return {
            'columns': columns,
            'rows': rows,
            'floors': floors,
            'total_halls': len(hall_names),
            'halls_per_floor': columns * rows,
            'valid': True,
            'error': None
        }
    
    except ValueError as e:
        return {
            'columns': 0,
            'rows': 0,
            'floors': 0,
            'total_halls': 0,
            'halls_per_floor': 0,
            'valid': False,
            'error': str(e)
        }