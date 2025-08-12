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


def calculate_riser_count(columns: int, rows: int, shared_risers: bool = True) -> int:
    """
    Calculate number of risers based on layout and sharing strategy.
    
    Args:
        columns: Number of columns in layout
        rows: Number of rows in layout  
        shared_risers: If True, use shared model (2*(C+R)), else unshared (4*(C+R))
    
    Returns:
        Number of risers required
    """
    if shared_risers:
        return 2 * (columns + rows)
    else:
        return 4 * (columns + rows)


def build_hall_table(columns: int, rows: int, floors: int, 
                    it_mw_data: Dict[str, float], 
                    fan_percent: float = 5.0,
                    misc_load_mw: float = 0.0,
                    misc_per_hall: bool = True,
                    include_floors: bool = True) -> pd.DataFrame:
    """
    Build comprehensive hall table with all load calculations.
    
    Args:
        columns: Number of columns
        rows: Number of rows
        floors: Number of floors
        it_mw_data: Dictionary of hall name -> IT MW
        fan_percent: Fan heat percentage (default 5%)
        misc_load_mw: Miscellaneous load in MW
        misc_per_hall: If True, misc load applied per hall, else total building
        include_floors: Whether hall names include floor numbers
        
    Returns:
        DataFrame with columns: Hall, Column, Row, Floor, IT_MW, Fan_MW, Misc_MW, Total_Cooling_MW
    """
    hall_names = make_hall_names(columns, rows, floors, include_floors)
    
    hall_data = []
    total_halls = len(hall_names)
    misc_per_hall_mw = misc_load_mw / total_halls if misc_per_hall else 0
    building_misc_per_hall = misc_load_mw / total_halls if not misc_per_hall else 0
    
    for hall_name in hall_names:
        # Extract position info from hall name
        if include_floors and '-F' in hall_name:
            base_name, floor_str = hall_name.split('-F')
            floor_num = int(floor_str)
        else:
            base_name = hall_name
            floor_num = 1
        
        # Extract column and row from base name (e.g., "A1" -> column="A", row=1)
        column_str = ''
        row_str = ''
        for char in base_name:
            if char.isalpha():
                column_str += char
            else:
                row_str += char
        
        row_num = int(row_str) if row_str else 1
        
        # Get IT load
        it_mw = it_mw_data.get(hall_name, 0.0)
        
        # Calculate fan load (percentage of IT load)
        fan_mw = it_mw * (fan_percent / 100)
        
        # Calculate misc load
        if misc_per_hall:
            misc_mw = misc_per_hall_mw
        else:
            misc_mw = building_misc_per_hall
            
        # Total cooling load
        total_cooling_mw = it_mw + fan_mw + misc_mw
        
        hall_data.append({
            'Hall': hall_name,
            'Column': column_str,
            'Row': row_num,
            'Floor': floor_num,
            'IT_MW': it_mw,
            'Fan_MW': fan_mw,
            'Misc_MW': misc_mw,
            'Total_Cooling_MW': total_cooling_mw
        })
    
    return pd.DataFrame(hall_data)


def calculate_riser_reduction_schedule(hall_table: pd.DataFrame, 
                                     columns: int, rows: int, floors: int) -> pd.DataFrame:
    """
    Calculate riser load reduction schedule showing load at each floor level.
    
    Args:
        hall_table: Hall table with cooling loads
        columns: Number of columns
        rows: Number of rows  
        floors: Number of floors
        
    Returns:
        DataFrame with columns: Column, Floor, Floor_Load_MW, Cumulative_Load_MW, Remaining_Load_MW
    """
    reduction_data = []
    
    # Group halls by column
    for column in hall_table['Column'].unique():
        column_halls = hall_table[hall_table['Column'] == column].copy()
        
        # Calculate total column load
        total_column_load = column_halls['Total_Cooling_MW'].sum()
        
        # Sort by floor (top floor first for reduction calculation)
        column_halls = column_halls.sort_values('Floor', ascending=False)
        
        cumulative_served = 0
        
        # Calculate load at each floor level (from top down)
        for floor in sorted(column_halls['Floor'].unique(), reverse=True):
            floor_halls = column_halls[column_halls['Floor'] == floor]
            floor_load = floor_halls['Total_Cooling_MW'].sum()
            
            # Remaining load = total load from this floor and below
            remaining_load = total_column_load - cumulative_served
            cumulative_served += floor_load
            
            reduction_data.append({
                'Column': column,
                'Floor': floor,
                'Floor_Load_MW': floor_load,
                'Cumulative_Load_MW': cumulative_served,
                'Remaining_Load_MW': remaining_load
            })
    
    # Sort by column then floor (ascending for display)
    df = pd.DataFrame(reduction_data)
    if not df.empty:
        df = df.sort_values(['Column', 'Floor'], ascending=[True, True])
    
    return df


def get_column_summary(hall_table: pd.DataFrame) -> pd.DataFrame:
    """
    Get summary of loads by column for riser sizing.
    
    Args:
        hall_table: Hall table with cooling loads
        
    Returns:
        DataFrame with columns: Column, Total_IT_MW, Total_Fan_MW, Total_Misc_MW, Total_Cooling_MW, Hall_Count
    """
    if hall_table.empty:
        return pd.DataFrame(columns=['Column', 'Total_IT_MW', 'Total_Fan_MW', 'Total_Misc_MW', 'Total_Cooling_MW', 'Hall_Count'])
    
    summary = hall_table.groupby('Column').agg({
        'IT_MW': 'sum',
        'Fan_MW': 'sum', 
        'Misc_MW': 'sum',
        'Total_Cooling_MW': 'sum',
        'Hall': 'count'
    }).reset_index()
    
    summary.columns = ['Column', 'Total_IT_MW', 'Total_Fan_MW', 'Total_Misc_MW', 'Total_Cooling_MW', 'Hall_Count']
    
    return summary.sort_values('Column')


def get_layout_stats(layout_str: str, include_floors: bool = True) -> Dict[str, any]:
    """
    Get statistics about a layout configuration including riser counts.
    
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
            'shared_risers': calculate_riser_count(columns, rows, True),
            'unshared_risers': calculate_riser_count(columns, rows, False),
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
            'shared_risers': 0,
            'unshared_risers': 0,
            'valid': False,
            'error': str(e)
        }