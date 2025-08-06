"""
Visualization module for pipe sizing charts and graphs.
"""

import matplotlib.pyplot as plt
import numpy as np
import math

def create_velocity_diameter_chart(flow_rate_gpm, max_velocity=15, save_path=None):
    """
    Create a velocity vs diameter chart for a given flow rate.
    
    Args:
        flow_rate_gpm: Flow rate in GPM
        max_velocity: Maximum velocity to plot (ft/s)
        save_path: Optional path to save the chart
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
    
    plt.figure(figsize=(12, 8))
    plt.plot(diameters_in, velocities, 'b-', linewidth=2, label='Velocity vs Diameter')
    plt.scatter(standard_sizes, standard_velocities, color='red', s=50, zorder=5, label='Standard Pipe Sizes')
    
    # Add velocity guidelines
    plt.axhline(y=6, color='green', linestyle='--', alpha=0.7, label='Typical Min Velocity (6 ft/s)')
    plt.axhline(y=12, color='orange', linestyle='--', alpha=0.7, label='Typical Max Velocity (12 ft/s)')
    
    plt.xlabel('Pipe Diameter (inches)', fontsize=12)
    plt.ylabel('Velocity (ft/s)', fontsize=12)
    plt.title(f'Pipe Velocity vs Diameter\\nFlow Rate: {flow_rate_gpm:,.0f} GPM', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    
    # Set reasonable axis limits
    plt.xlim(6, 48)
    plt.ylim(0, max_velocity)
    
    # Add annotations for standard sizes
    for i, (size, vel) in enumerate(zip(standard_sizes, standard_velocities)):
        if vel <= max_velocity:
            plt.annotate(f'{size}"', (size, vel), xytext=(5, 5), 
                        textcoords='offset points', fontsize=8, alpha=0.8)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return plt

def create_pressure_drop_chart(diameter_range=(6, 48), velocity=10, density=62.4, viscosity=2.73e-5, save_path=None):
    """
    Create a pressure drop per 100 ft chart for different pipe diameters.
    
    Args:
        diameter_range: Tuple of (min, max) diameter in inches
        velocity: Velocity in ft/s
        density: Fluid density in lb/ft³
        viscosity: Dynamic viscosity in lb/ft·s
        save_path: Optional path to save the chart
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
    
    plt.figure(figsize=(12, 8))
    plt.plot(diameters_in, pressure_drops, 'b-', linewidth=2, label='Pressure Drop vs Diameter')
    plt.scatter(standard_sizes, standard_dp, color='red', s=50, zorder=5, label='Standard Pipe Sizes')
    
    # Add pressure drop guidelines
    plt.axhline(y=5, color='green', linestyle='--', alpha=0.7, label='Low ΔP (5 psi/100ft)')
    plt.axhline(y=10, color='orange', linestyle='--', alpha=0.7, label='Moderate ΔP (10 psi/100ft)')
    plt.axhline(y=20, color='red', linestyle='--', alpha=0.7, label='High ΔP (20 psi/100ft)')
    
    plt.xlabel('Pipe Diameter (inches)', fontsize=12)
    plt.ylabel('Pressure Drop (psi per 100 ft)', fontsize=12)
    plt.title(f'Pressure Drop vs Pipe Diameter\\nVelocity: {velocity} ft/s, Fluid: Water', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    
    plt.xlim(diameter_range[0], diameter_range[1])
    plt.ylim(0, max(pressure_drops) * 1.1)
    
    # Add annotations for standard sizes
    for i, (size, dp) in enumerate(zip(standard_sizes, standard_dp)):
        if diameter_range[0] <= size <= diameter_range[1]:
            plt.annotate(f'{size}"\\n{dp:.1f} psi', (size, dp), xytext=(5, 5), 
                        textcoords='offset points', fontsize=8, alpha=0.8, ha='left')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return plt

def show_charts():
    """Display all generated charts."""
    plt.show()

def save_all_charts(flow_rate_gpm, velocity, density, viscosity, output_dir="charts"):
    """
    Generate and save both velocity and pressure drop charts.
    """
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Velocity vs Diameter chart
    vel_chart = create_velocity_diameter_chart(
        flow_rate_gpm, 
        save_path=f"{output_dir}/velocity_vs_diameter.png"
    )
    plt.close()
    
    # Pressure Drop chart  
    dp_chart = create_pressure_drop_chart(
        velocity=velocity,
        density=density,
        viscosity=viscosity,
        save_path=f"{output_dir}/pressure_drop_vs_diameter.png"
    )
    plt.close()
    
    print(f"\nCharts saved to '{output_dir}' directory:")
    print(f"- velocity_vs_diameter.png")
    print(f"- pressure_drop_vs_diameter.png")