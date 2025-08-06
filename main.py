#!/usr/bin/env python3
"""
Main script for Data Center Pipe Sizer tool.
"""

import math
from calc.inputs import get_inputs
from calc.pipe_lookup import get_nominal_pipe_size, get_pipe_id
from chiller_sizing import chiller_sizing

try:
    from calc.visualization import create_velocity_diameter_chart, create_pressure_drop_chart, show_charts, save_all_charts
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

def pipeline_sizing(mass_flow_rate, density, viscosity, max_pressure_drop, max_velocity):
    """
    Perform pipeline sizing based on Imperial units.
    Inputs:
        mass_flow_rate: lb/hr
        density: lb/ft³
        viscosity: lb/ft·s
        max_pressure_drop: lb/ft²
        max_velocity: ft/s
    Outputs are all Imperial: in, ft/s, psi, etc.
    """
    def reynolds_number(diameter, velocity):
        return (density * velocity * diameter) / viscosity

    def friction_factor(re):
        if re < 2000:
            return 64 / re
        return 0.3164 / (re ** 0.25)

    def pressure_drop(f, velocity, diameter):
        # Use standard 100 ft equivalent length for sizing
        pipe_length = 100  # ft
        return f * (pipe_length / diameter) * (density * velocity**2 / 2)

    diameter = 0.5  # initial guess in feet (~6 in)
    while True:
        area = math.pi * (diameter / 2) ** 2  # ft²
        velocity = (mass_flow_rate / 3600) / (density * area)  # ft/s

        if velocity > max_velocity:
            diameter += 0.01
            continue

        re = reynolds_number(diameter, velocity)
        f = friction_factor(re)
        dp = pressure_drop(f, velocity, diameter)

        if dp > max_pressure_drop:
            diameter += 0.01
            continue

        break

    calculated_diameter_in = diameter * 12
    nominal_size = get_nominal_pipe_size(calculated_diameter_in)
    actual_diameter_in = get_pipe_id(nominal_size)
    
    if actual_diameter_in is None:
        # Fallback to calculated diameter if no standard size found
        # Calculate flow rate in GPM for fallback case
        flow_rate_gpm = (mass_flow_rate / 3600) * (1 / density) * 7.48 * 60
        return {
            "Pipe Diameter (in)": round(calculated_diameter_in, 1),
            "Flow Rate (GPM)": round(flow_rate_gpm, 0),
            "Velocity (ft/s)": round(velocity, 1),
            "Reynolds Number": round(re, 0),
            "Friction Factor": round(f, 4),
            "Pressure Drop (psi)": round(dp / 144, 1),
        }
    
    # Recalculate velocity with actual pipe diameter
    actual_diameter_ft = actual_diameter_in / 12
    actual_area = math.pi * (actual_diameter_ft / 2) ** 2
    actual_velocity = (mass_flow_rate / 3600) / (density * actual_area)
    
    # Recalculate pressure drop with actual values
    actual_re = reynolds_number(actual_diameter_ft, actual_velocity)
    actual_f = friction_factor(actual_re)
    actual_dp = pressure_drop(actual_f, actual_velocity, actual_diameter_ft)
    
    # Calculate flow rate in GPM
    flow_rate_gpm = (mass_flow_rate / 3600) * (1 / density) * 7.48 * 60  # Convert lb/hr to GPM
    
    return {
        "Standard Pipe Size": nominal_size,
        "Actual Pipe ID (in)": round(actual_diameter_in, 1),
        "Flow Rate (GPM)": round(flow_rate_gpm, 0),
        "Velocity (ft/s)": round(actual_velocity, 1),
        "Reynolds Number": round(actual_re, 0),
        "Friction Factor": round(actual_f, 4),
        "Pressure Drop (psi)": round(actual_dp / 144, 1),
    }

if __name__ == "__main__":
    inputs = get_inputs()

    # Convert MW to BTU/hr: 1 MW = 3.412e6 BTU/hr
    btu_hr = inputs["mw"] * 3.412e6
    mass_flow_rate = btu_hr / (inputs["delta_t"] * 1.0)  # BTU/hr ÷ (ΔT × Cp)

    # Use density in lb/ft³ directly
    result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=inputs["density"],
        viscosity=inputs["viscosity"],
        max_pressure_drop=inputs["max_dp"] * 144,  # psi to lb/ft²
        max_velocity=inputs["velocity"]
    )
    print("\n=== PIPE SIZING RESULTS ===")
    print("Main Distribution Pipe:")
    for key, value in result.items():
        print(f"{key}: {value}")
    
    # If risers are specified, size individual risers
    if inputs["num_risers"]:
        print(f"\n=== RISER SIZING ({inputs['num_risers']} risers) ===")
        riser_flow_rate = mass_flow_rate / inputs["num_risers"]  # Divide total flow among risers
        
        riser_result = pipeline_sizing(
            mass_flow_rate=riser_flow_rate,
            density=inputs["density"],
            viscosity=inputs["viscosity"],
            max_pressure_drop=inputs["max_dp"] * 144,  # psi to lb/ft²
            max_velocity=inputs["velocity"]
        )
        
        print(f"Each riser ({inputs['num_risers']} total):")
        for key, value in riser_result.items():
            print(f"{key}: {value}")
    
    # Display chiller sizing recommendations
    print("\n=== CHILLER SIZING RECOMMENDATIONS ===")
    chiller_results = chiller_sizing(inputs["mw"])
    
    if chiller_results:
        # Show top 3 options
        print("\nTop Chiller Configuration Options:")
        print("Option | Chiller | Total | Operating | Spare | Total    | Loading | Redundancy")
        print("       | Size MW | Count | Chillers  | Units | Capacity | %       | %")
        print("-" * 75)
        
        for i, option in enumerate(chiller_results[:3], 1):
            print(f"{i:6d} | {option['chiller_size_mw']:7.1f} | "
                  f"{option['total_chillers']:5d} | {option['operating_chillers']:9d} | "
                  f"{option['spare_chillers']:5d} | {option['total_capacity_mw']:8.1f} | "
                  f"{option['loading_percent']:7.1f} | {option['redundancy_percent']:10.1f}")
        
        # Show recommendation
        best_option = chiller_results[0]
        print(f"\nRecommended Configuration:")
        print(f"Install {best_option['total_chillers']} x {best_option['chiller_size_mw']} MW chillers")
        print(f"Operating: {best_option['operating_chillers']} chillers + {best_option['spare_chillers']} spare")
        print(f"Total capacity: {best_option['total_capacity_mw']} MW")
        print(f"Operating load: {best_option['loading_percent']}%")
    else:
        print("No suitable chiller configurations found.")
    
    # Generate visualization charts if available
    if VISUALIZATION_AVAILABLE:
        print("\n=== GENERATING CHARTS ===")
        try:
            # Get flow rate from main pipe result
            main_flow_gpm = result.get('Flow Rate (GPM)', 0)
            
            # Create charts
            print("Creating velocity vs diameter chart...")
            create_velocity_diameter_chart(main_flow_gpm)
            
            print("Creating pressure drop chart...")
            create_pressure_drop_chart(
                velocity=inputs['velocity'],
                density=inputs['density'], 
                viscosity=inputs['viscosity']
            )
            
            # Ask user if they want to save or display charts
            chart_action = input("\nSave charts to files (s), display charts (d), or skip (Enter): ").lower().strip()
            
            if chart_action == 's':
                save_all_charts(
                    flow_rate_gpm=main_flow_gpm,
                    velocity=inputs['velocity'],
                    density=inputs['density'],
                    viscosity=inputs['viscosity']
                )
            elif chart_action == 'd':
                print("Displaying charts... (close chart windows to continue)")
                show_charts()
            else:
                print("Charts generated but not saved or displayed.")
                
        except Exception as e:
            print(f"Error generating charts: {e}")
    else:
        print("\n=== CHARTS UNAVAILABLE ===")
        print("Matplotlib not installed. To enable charts, run: pip install matplotlib")
