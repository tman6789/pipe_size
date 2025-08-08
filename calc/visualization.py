"""
Visualization module for pipe sizing charts and graphs using Plotly.

V2 Features:
- Plotly interactive charts for web deployment
- Layout heatmaps for data center visualization
- Riser stack bar charts
- Professional styling with plotly_white theme
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import math
from typing import Optional, Dict, List, Tuple


def velocity_figure(flow_rate_gpm: float, delta_t_f: float = 15.0, max_velocity: float = 15.0) -> go.Figure:
    """
    Create interactive velocity vs diameter chart using Plotly.
    
    Args:
        flow_rate_gpm: Flow rate in GPM
        delta_t_f: Temperature difference for context in title
        max_velocity: Maximum velocity to plot (ft/s)
    
    Returns:
        Plotly Figure object
    """
    # Convert GPM to ft³/s
    flow_rate_cfs = flow_rate_gpm / 448.831
    
    # Range of pipe diameters (inches)
    diameters_in = np.linspace(6, 48, 100)
    diameters_ft = diameters_in / 12
    
    # Calculate velocities for each diameter
    velocities = []
    for d_ft in diameters_ft:
        area_ft2 = math.pi * (d_ft / 2) ** 2
        velocity = flow_rate_cfs / area_ft2
        velocities.append(velocity)
    
    # Standard pipe sizes for reference
    standard_sizes = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36, 42, 48]
    standard_velocities = []
    for size in standard_sizes:
        d_ft = size / 12
        area_ft2 = math.pi * (d_ft / 2) ** 2
        vel = flow_rate_cfs / area_ft2
        standard_velocities.append(vel)
    
    fig = go.Figure()
    
    # Main velocity curve
    fig.add_trace(go.Scatter(
        x=diameters_in,
        y=velocities,
        mode='lines',
        name='Velocity vs Diameter',
        line=dict(color='blue', width=2),
        hovertemplate='Diameter: %{x:.1f}"<br>Velocity: %{y:.1f} ft/s<extra></extra>'
    ))
    
    # Standard pipe sizes as scatter points
    fig.add_trace(go.Scatter(
        x=standard_sizes,
        y=standard_velocities,
        mode='markers+text',
        name='Standard Sizes',
        marker=dict(color='red', size=8),
        text=[f'{size}"' for size in standard_sizes],
        textposition='top center',
        hovertemplate='Standard Size: %{text}<br>Velocity: %{y:.1f} ft/s<extra></extra>'
    ))
    
    # Add velocity guideline lines
    fig.add_hline(y=6, line_dash="dash", line_color="green", 
                  annotation_text="Min Velocity (6 ft/s)", annotation_position="right")
    fig.add_hline(y=10, line_dash="dash", line_color="orange",
                  annotation_text="High Velocity Warning (10 ft/s)", annotation_position="right") 
    fig.add_hline(y=12, line_dash="dash", line_color="red",
                  annotation_text="Typical Max (12 ft/s)", annotation_position="right")
    
    fig.update_layout(
        template='plotly_white',
        title=f'Pipe Velocity vs Diameter<br>Flow: {flow_rate_gpm:,.0f} GPM, ΔT: {delta_t_f}°F',
        xaxis_title='Pipe Diameter (inches)',
        yaxis_title='Velocity (ft/s)',
        showlegend=True,
        height=500,
        xaxis=dict(range=[6, 48], gridcolor='lightgray'),
        yaxis=dict(range=[0, max_velocity], gridcolor='lightgray')
    )
    
    return fig


def dp_figure(velocity: float = 10.0, density: float = 62.4, viscosity: float = 2.73e-5,
              delta_t_f: float = 15.0, diameter_range: Tuple[float, float] = (6, 48)) -> go.Figure:
    """
    Create interactive pressure drop vs diameter chart using Plotly.
    
    Args:
        velocity: Velocity in ft/s
        density: Fluid density in lb/ft³
        viscosity: Dynamic viscosity in lb/ft·s  
        delta_t_f: Temperature difference for context in title
        diameter_range: Tuple of (min, max) diameter in inches
    
    Returns:
        Plotly Figure object
    """
    # Range of pipe diameters (inches)
    diameters_in = np.linspace(diameter_range[0], diameter_range[1], 100)
    diameters_ft = diameters_in / 12
    
    pressure_drops = []
    for d_ft in diameters_ft:
        # Calculate Reynolds number
        re = (density * velocity * d_ft) / viscosity
        
        # Calculate friction factor
        if re < 2000:
            f = 64 / re
        else:
            f = 0.3164 / (re ** 0.25)
        
        # Calculate pressure drop per 100 ft
        pipe_length = 100  # ft
        dp = f * (pipe_length / d_ft) * (density * velocity**2 / 2)
        dp_psi = dp / 144  # Convert to psi
        pressure_drops.append(dp_psi)
    
    # Standard pipe sizes
    standard_sizes = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36, 42, 48]
    standard_dp = []
    for size in standard_sizes:
        d_ft = size / 12
        re = (density * velocity * d_ft) / viscosity
        f = 64 / re if re < 2000 else 0.3164 / (re ** 0.25)
        dp = f * (100 / d_ft) * (density * velocity**2 / 2)
        dp_psi = dp / 144
        standard_dp.append(dp_psi)
    
    fig = go.Figure()
    
    # Main pressure drop curve
    fig.add_trace(go.Scatter(
        x=diameters_in,
        y=pressure_drops,
        mode='lines',
        name='Pressure Drop vs Diameter',
        line=dict(color='blue', width=2),
        hovertemplate='Diameter: %{x:.1f}"<br>ΔP: %{y:.2f} psi/100ft<extra></extra>'
    ))
    
    # Standard pipe sizes as scatter points
    fig.add_trace(go.Scatter(
        x=standard_sizes,
        y=standard_dp,
        mode='markers+text',
        name='Standard Sizes',
        marker=dict(color='red', size=8),
        text=[f'{size}"<br>{dp:.1f}' for size, dp in zip(standard_sizes, standard_dp)],
        textposition='top center',
        hovertemplate='Standard Size: %{x}"<br>ΔP: %{y:.2f} psi/100ft<extra></extra>'
    ))
    
    # Add pressure drop guideline lines
    fig.add_hline(y=5, line_dash="dash", line_color="green",
                  annotation_text="Low ΔP (5 psi/100ft)", annotation_position="right")
    fig.add_hline(y=10, line_dash="dash", line_color="orange",
                  annotation_text="Moderate ΔP (10 psi/100ft)", annotation_position="right")
    fig.add_hline(y=20, line_dash="dash", line_color="red",
                  annotation_text="High ΔP (20 psi/100ft)", annotation_position="right")
    
    fig.update_layout(
        template='plotly_white',
        title=f'Pressure Drop vs Pipe Diameter<br>Velocity: {velocity} ft/s, ΔT: {delta_t_f}°F',
        xaxis_title='Pipe Diameter (inches)',
        yaxis_title='Pressure Drop (psi per 100 ft)',
        showlegend=True,
        height=500,
        xaxis=dict(range=list(diameter_range), gridcolor='lightgray'),
        yaxis=dict(range=[0, max(pressure_drops) * 1.1], gridcolor='lightgray')
    )
    
    return fig


def layout_heatmap(columns: int, rows: int, floors: int, hall_loads: Dict[str, float] = None,
                   riser_placement: str = "corners", include_floors: bool = True) -> go.Figure:
    """
    Create layout heatmap visualization for data center halls.
    
    Args:
        columns: Number of columns
        rows: Number of rows  
        floors: Number of floors
        hall_loads: Dictionary mapping hall names to MW loads
        riser_placement: Riser placement strategy ("corners", "edges", "center")
        include_floors: Whether to show floors separately
    
    Returns:
        Plotly Figure object
    """
    from .layout import make_hall_names
    
    if hall_loads is None:
        hall_loads = {}
    
    # Generate subplot for each floor if floors > 1
    if floors > 1 and include_floors:
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=1, cols=floors,
            subplot_titles=[f'Floor {i+1}' for i in range(floors)],
            horizontal_spacing=0.05
        )
        
        for floor in range(floors):
            floor_data = []
            floor_text = []
            
            for row in range(rows):
                row_data = []
                row_text = []
                for col in range(columns):
                    # Generate hall name for this position
                    col_letter = chr(ord('A') + col) if col < 26 else f'A{col-25}'
                    hall_name = f"{col_letter}{row+1}-F{floor+1}"
                    
                    load = hall_loads.get(hall_name, 0)
                    row_data.append(load)
                    row_text.append(f"{hall_name}<br>{load:.1f} MW")
                    
                floor_data.append(row_data)
                floor_text.append(row_text)
            
            fig.add_trace(
                go.Heatmap(
                    z=floor_data,
                    text=floor_text,
                    texttemplate='%{text}',
                    textfont=dict(size=10),
                    colorscale='Viridis',
                    showscale=(floor == 0),  # Only show colorbar on first plot
                    hovertemplate='Hall: %{text}<extra></extra>'
                ),
                row=1, col=floor+1
            )
            
            # Add riser markers based on placement strategy
            if riser_placement == "corners":
                riser_x = [0, columns-1, 0, columns-1]
                riser_y = [0, 0, rows-1, rows-1]
            elif riser_placement == "edges":
                riser_x = [0, columns//2, columns-1, columns//2]
                riser_y = [rows//2, 0, rows//2, rows-1]
            else:  # center
                riser_x = [columns//2]
                riser_y = [rows//2]
            
            fig.add_trace(
                go.Scatter(
                    x=riser_x, y=riser_y,
                    mode='markers',
                    marker=dict(symbol='square', size=15, color='red', 
                               line=dict(color='white', width=2)),
                    name='Risers' if floor == 0 else '',
                    showlegend=(floor == 0),
                    hovertemplate='Riser Location<extra></extra>'
                ),
                row=1, col=floor+1
            )
    
    else:
        # Single floor layout
        floor_data = []
        floor_text = []
        
        for row in range(rows):
            row_data = []
            row_text = []
            for col in range(columns):
                col_letter = chr(ord('A') + col) if col < 26 else f'A{col-25}'
                hall_name = f"{col_letter}{row+1}" + (f"-F1" if include_floors else "")
                
                load = hall_loads.get(hall_name, 0)
                row_data.append(load)
                row_text.append(f"{hall_name}<br>{load:.1f} MW")
                
            floor_data.append(row_data)
            floor_text.append(row_text)
        
        fig = go.Figure()
        
        fig.add_trace(go.Heatmap(
            z=floor_data,
            text=floor_text,
            texttemplate='%{text}',
            textfont=dict(size=10),
            colorscale='Viridis',
            hovertemplate='Hall: %{text}<extra></extra>'
        ))
        
        # Add riser markers
        if riser_placement == "corners":
            riser_x = [0, columns-1, 0, columns-1]
            riser_y = [0, 0, rows-1, rows-1]
        elif riser_placement == "edges":
            riser_x = [0, columns//2, columns-1, columns//2] 
            riser_y = [rows//2, 0, rows//2, rows-1]
        else:  # center
            riser_x = [columns//2]
            riser_y = [rows//2]
        
        fig.add_trace(go.Scatter(
            x=riser_x, y=riser_y,
            mode='markers',
            marker=dict(symbol='square', size=15, color='red',
                       line=dict(color='white', width=2)),
            name='Risers',
            hovertemplate='Riser Location<extra></extra>'
        ))
    
    fig.update_layout(
        template='plotly_white',
        title=f'Data Center Layout: {columns}×{rows}×{floors}',
        height=400 + (floors - 1) * 100,
        showlegend=True
    )
    
    return fig


def riser_stack_bar(riser_data: pd.DataFrame) -> go.Figure:
    """
    Create bar chart for riser stack analysis.
    
    Args:
        riser_data: DataFrame with columns ['Column', 'Total_MW', 'GPM', 'Nominal', 'Velocity', 'DP_per_100ft']
    
    Returns:
        Plotly Figure object
    """
    if riser_data.empty:
        fig = go.Figure()
        fig.update_layout(
            template='plotly_white',
            title='No Riser Data Available',
            height=400
        )
        return fig
    
    fig = go.Figure()
    
    # MW Load bars
    fig.add_trace(go.Bar(
        x=riser_data['Column'],
        y=riser_data['Total_MW'],
        name='MW Load',
        marker_color='lightblue',
        yaxis='y',
        hovertemplate='Column %{x}<br>Load: %{y:.1f} MW<extra></extra>'
    ))
    
    # GPM bars (secondary axis)  
    fig.add_trace(go.Bar(
        x=riser_data['Column'],
        y=riser_data['GPM'],
        name='GPM',
        marker_color='orange',
        opacity=0.7,
        yaxis='y2',
        hovertemplate='Column %{x}<br>Flow: %{y:.0f} GPM<extra></extra>'
    ))
    
    fig.update_layout(
        template='plotly_white',
        title='Riser Stack Analysis by Column',
        xaxis_title='Column',
        yaxis=dict(title='MW Load', side='left', color='blue'),
        yaxis2=dict(title='GPM', side='right', overlaying='y', color='orange'),
        barmode='group',
        height=500,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


# Legacy compatibility functions (deprecated)
def create_velocity_diameter_chart(*args, **kwargs):
    """Legacy function - use velocity_figure instead."""
    return velocity_figure(*args, **kwargs)


def create_pressure_drop_chart(*args, **kwargs):
    """Legacy function - use dp_figure instead."""  
    return dp_figure(*args, **kwargs)