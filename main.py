#!/usr/bin/env python3
"""
Data Center Pipe Sizer V2 - Enhanced CLI Calculator

Features:
- Layout-based sizing (C×R×F format)
- Per-hall MW inputs or uniform distribution
- Riser sharing analysis
- Enhanced input validation and flow control
- Integrated visualization and reporting
"""

import math
import os
import sys
from typing import Dict, List, Optional, Tuple
from calc.pipe_lookup import get_nominal_pipe_size, get_pipe_id
from calc.fluid_properties import get_fluid_options, get_fluid_properties, get_fluid_name
from calc.flow import mw_to_gpm
from calc.layout import (
    parse_layout, make_hall_names, column_aggregates, 
    create_hall_dataframe, validate_hall_data
)
from chiller_sizing import advanced_chiller_sizing, ChillerStrategy, RedundancyModel

# Check for visualization availability
try:
    from calc.visualization import velocity_figure, dp_figure, layout_heatmap, riser_stack_bar
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("Warning: Plotly not available. Charts will be skipped.")

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

def display_welcome():
    """Display welcome message and V2 features."""
    print("="*70)
    print("🏢 DATA CENTER PIPE SIZER V2")
    print("="*70)
    print("Professional chilled-water piping and chiller sizing tool")
    print("\nV2 Features:")
    print("• Layout-based sizing (C×R×F format)")
    print("• Per-hall MW loads with fan heat factor")
    print("• Shared riser analysis by column")
    print("• Enhanced velocity warnings and ΔP normalization")
    print("• Integrated chiller sizing with tons")
    print("="*70)


def get_menu_choice() -> int:
    """Get main menu selection from user."""
    print("\n🔧 CALCULATION OPTIONS:")
    print("1. Quick Sizing (Simple MW + ΔT)")
    print("2. Layout-Based Analysis (Advanced)")
    print("3. V2 Web Interface Help")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nSelect option [1-4]: ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            else:
                print("Please enter 1, 2, 3, or 4")
        except (ValueError, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            sys.exit(0)


def get_fluid_selection() -> Tuple[str, float, float]:
    """Get fluid selection and properties."""
    print("\n💧 FLUID SELECTION:")
    fluid_options = get_fluid_options()
    
    for i, fluid_type in enumerate(fluid_options, 1):
        fluid_name = get_fluid_name(fluid_type)
        print(f"{i}. {fluid_name}")
    
    while True:
        try:
            choice = input("Select fluid type [default 1]: ").strip() or "1"
            fluid_idx = int(choice) - 1
            if 0 <= fluid_idx < len(fluid_options):
                selected_fluid = fluid_options[fluid_idx]
                density, viscosity = get_fluid_properties(selected_fluid)
                fluid_name = get_fluid_name(selected_fluid)
                print(f"✅ Using {fluid_name} (ρ={density} lb/ft³, μ={viscosity:.2e} lb/ft·s)")
                return selected_fluid, density, viscosity
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def get_basic_inputs() -> Dict:
    """Get basic sizing inputs for quick mode."""
    print("\n⚡ BASIC INPUTS:")
    
    while True:
        try:
            mw = float(input("Total Cooling Load (MW): "))
            if mw > 0:
                break
            print("Cooling load must be positive.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            delta_t = float(input("ΔT (°F) [default 15]: ") or 15)
            if delta_t > 0:
                break
            print("Temperature difference must be positive.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            velocity = float(input("Target Velocity (ft/s) [default 12]: ") or 12)
            if 3 <= velocity <= 20:
                break
            print("Velocity should be between 3-20 ft/s for good practice.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            max_dp = float(input("Max Pressure Drop (psi/100ft) [default 20]: ") or 20)
            if max_dp > 0:
                break
            print("Pressure drop must be positive.")
        except ValueError:
            print("Please enter a valid number.")
    
    return {
        'mw': mw,
        'delta_t': delta_t, 
        'velocity': velocity,
        'max_dp': max_dp
    }


def get_layout_inputs() -> Dict:
    """Get layout-based inputs for advanced mode."""
    print("\n🏗️ LAYOUT CONFIGURATION:")
    
    # Get layout specification
    while True:
        layout_str = input("Data center layout (C×R×F, e.g. 4×3×2): ").strip()
        try:
            columns, rows, floors = parse_layout(layout_str)
            total_halls = columns * rows * floors
            print(f"✅ Layout: {columns} columns × {rows} rows × {floors} floors = {total_halls} halls")
            break
        except ValueError as e:
            print(f"❌ {e}")
            print("Please use format like '4×3×2' or '4x3x2'")
    
    # Include floors in names
    include_floors = input("Include floor numbers in hall names? [y/N]: ").lower().startswith('y')
    
    # MW distribution method
    use_same_mw = input("Use same MW for all halls? [Y/n]: ").lower() not in ['n', 'no']
    
    hall_loads = {}
    if use_same_mw:
        while True:
            try:
                mw_per_hall = float(input("IT Load per hall (MW): "))
                if mw_per_hall >= 0:
                    break
                print("MW load must be non-negative.")
            except ValueError:
                print("Please enter a valid number.")
        
        hall_names = make_hall_names(columns, rows, floors, include_floors)
        hall_loads = {name: mw_per_hall for name in hall_names}
    else:
        # Individual hall inputs (simplified for CLI)
        hall_names = make_hall_names(columns, rows, floors, include_floors)
        print(f"\n📝 Enter IT Load (MW) for each hall:")
        for hall_name in hall_names:
            while True:
                try:
                    mw = float(input(f"{hall_name}: "))
                    if mw >= 0:
                        hall_loads[hall_name] = mw
                        break
                    print("MW load must be non-negative.")
                except ValueError:
                    print("Please enter a valid number.")
    
    # Fan heat factor
    while True:
        try:
            fan_heat_pct = float(input("Fan heat percentage (0-20%) [default 5]: ") or 5)
            if 0 <= fan_heat_pct <= 20:
                break
            print("Fan heat should be between 0-20%.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Basic sizing parameters
    basic_params = get_basic_inputs()
    
    # Riser configuration
    shared_risers = input("\n🏗️ Use shared risers among halls? [Y/n]: ").lower() not in ['n', 'no']
    
    return {
        **basic_params,
        'layout': (columns, rows, floors),
        'include_floors': include_floors,
        'hall_loads': hall_loads,
        'fan_heat_pct': fan_heat_pct,
        'shared_risers': shared_risers,
        'total_it_mw': sum(hall_loads.values()),
        'total_cooling_mw': sum(hall_loads.values()) * (1 + fan_heat_pct/100)
    }


def run_quick_sizing():
    """Run quick sizing mode."""
    print("\n🚀 QUICK SIZING MODE")
    
    # Get inputs
    inputs = get_basic_inputs()
    fluid_type, density, viscosity = get_fluid_selection()
    
    # Calculate
    total_gpm = mw_to_gpm(inputs['mw'], inputs['delta_t'])
    btu_hr = inputs['mw'] * 3.412e6
    mass_flow_rate = btu_hr / (inputs['delta_t'] * 1.0)
    
    # Size main pipe
    result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=density,
        viscosity=viscosity,
        max_pressure_drop=inputs['max_dp'] * 144,
        max_velocity=inputs['velocity']
    )
    
    # Display results
    print("\n" + "="*50)
    print("📊 QUICK SIZING RESULTS")
    print("="*50)
    print(f"Total Load: {inputs['mw']} MW")
    print(f"Total Flow: {total_gpm:,.0f} GPM")
    print(f"ΔT: {inputs['delta_t']}°F")
    print(f"Fluid: {get_fluid_name(fluid_type)}")
    
    print("\n🔧 Main Distribution Pipe:")
    for key, value in result.items():
        if "Pressure Drop" in key:
            print(f"{key.replace('Pressure Drop', 'ΔP/100ft')}: {value}")
        else:
            print(f"{key}: {value}")
    
    # Check for warnings
    velocity = result.get('Velocity (ft/s)', 0)
    if velocity > 10:
        print(f"\n⚠️  WARNING: Velocity {velocity} ft/s exceeds 10 ft/s")
        print("   Consider larger pipe to reduce noise and erosion risk.")
    
    # Simple chiller sizing
    print("\n❄️  CHILLER RECOMMENDATIONS:")
    run_chiller_analysis(inputs['mw'])


def run_layout_analysis():
    """Run advanced layout-based analysis."""
    print("\n🏗️ LAYOUT-BASED ANALYSIS MODE")
    
    # Get inputs
    inputs = get_layout_inputs()
    fluid_type, density, viscosity = get_fluid_selection()
    
    columns, rows, floors = inputs['layout']
    hall_loads = inputs['hall_loads']
    
    print("\n" + "="*60)
    print("📊 LAYOUT ANALYSIS RESULTS")
    print("="*60)
    print(f"Layout: {columns}×{rows}×{floors} ({len(hall_loads)} halls)")
    print(f"Total IT Load: {inputs['total_it_mw']:.1f} MW")
    print(f"Total Cooling Load: {inputs['total_cooling_mw']:.1f} MW (includes {inputs['fan_heat_pct']}% fan heat)")
    print(f"Total Flow: {mw_to_gpm(inputs['total_cooling_mw'], inputs['delta_t']):,.0f} GPM")
    
    # Main distribution sizing
    total_gpm = mw_to_gpm(inputs['total_cooling_mw'], inputs['delta_t'])
    btu_hr = inputs['total_cooling_mw'] * 3.412e6
    mass_flow_rate = btu_hr / (inputs['delta_t'] * 1.0)
    
    main_result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=density,
        viscosity=viscosity,
        max_pressure_drop=inputs['max_dp'] * 144,
        max_velocity=inputs['velocity']
    )
    
    print("\n🔧 Main Distribution Pipe:")
    for key, value in main_result.items():
        if "Pressure Drop" in key:
            print(f"{key.replace('Pressure Drop', 'ΔP/100ft')}: {value}")
        else:
            print(f"{key}: {value}")
    
    # Riser analysis
    if inputs['shared_risers']:
        print("\n🏗️ SHARED RISER ANALYSIS (By Column):")
        
        # Create DataFrame for column aggregation
        import pandas as pd
        hall_df = pd.DataFrame([
            {'Hall': hall, 'IT Load (MW)': it_mw} 
            for hall, it_mw in hall_loads.items()
        ])
        
        col_agg = column_aggregates(hall_df, columns, rows, floors, inputs['include_floors'])
        
        if not col_agg.empty:
            print(f"{'Column':<8} {'IT MW':<8} {'Cooling MW':<12} {'GPM':<8} {'Pipe Size':<12} {'Velocity':<10} {'ΔP/100ft'}")
            print("-" * 70)
            
            warnings = []
            for _, row in col_agg.iterrows():
                col_it_mw = row['Total_MW']
                col_cooling_mw = col_it_mw * (1 + inputs['fan_heat_pct']/100)
                col_gpm = mw_to_gpm(col_cooling_mw, inputs['delta_t'])
                
                # Size riser for this column
                col_btu_hr = col_cooling_mw * 3.412e6
                col_mass_flow = col_btu_hr / (inputs['delta_t'] * 1.0)
                
                col_result = pipeline_sizing(
                    mass_flow_rate=col_mass_flow,
                    density=density,
                    viscosity=viscosity,
                    max_pressure_drop=inputs['max_dp'] * 144,
                    max_velocity=inputs['velocity']
                )
                
                pipe_size = col_result.get('Standard Pipe Size', 'N/A')
                velocity = col_result.get('Velocity (ft/s)', 0)
                dp_psi = col_result.get('Pressure Drop (psi)', 0)
                
                print(f"{row['Column']:<8} {col_it_mw:<8.1f} {col_cooling_mw:<12.1f} {col_gpm:<8.0f} {pipe_size:<12} {velocity:<10.1f} {dp_psi}")
                
                if velocity > 10:
                    warnings.append(f"Column {row['Column']}: velocity {velocity:.1f} ft/s > 10 ft/s")
            
            if warnings:
                print("\n⚠️  VELOCITY WARNINGS:")
                for warning in warnings:
                    print(f"   {warning}")
    
    else:
        print("\n🏠 INDIVIDUAL HALL ANALYSIS:")
        print("(Per-hall sizing not implemented in CLI - use Web Interface for full analysis)")
    
    # Chiller sizing
    print("\n❄️  CHILLER RECOMMENDATIONS:")
    run_chiller_analysis(inputs['total_cooling_mw'])


def run_chiller_analysis(cooling_mw: float):
    """Run chiller analysis and display results."""
    try:
        chiller_results = advanced_chiller_sizing(
            total_mw=cooling_mw,
            redundancy_model=RedundancyModel.N_PLUS_1,
            redundancy_percent=20.0,
            strategy=ChillerStrategy.BALANCED,
            max_chillers=20,
            electricity_rate=0.12
        )
        
        if chiller_results:
            print(f"{'#':<3} {'MW':<8} {'Tons':<8} {'Units':<6} {'Operating':<10} {'Loading%':<10} {'10-Yr TCO'}")
            print("-" * 65)
            
            for i, option in enumerate(chiller_results[:3], 1):
                mw_size = option['chiller_size_mw']
                tons = mw_size / 0.003517  # Convert MW to tons
                units = option['total_chillers']
                operating = option['operating_chillers']
                loading = option['loading_percent']
                tco = option.get('ten_year_tco', 0)
                
                print(f"{i:<3} {mw_size:<8.1f} {tons:<8.0f} {units:<6} {operating:<10} {loading:<10.1f}% ${tco:,.0f}")
            
            best = chiller_results[0]
            print(f"\n🎯 RECOMMENDATION: {best['total_chillers']} × {best['chiller_size_mw']:.1f} MW chillers")
            print(f"   ({best['operating_chillers']} operating + {best['redundant_chillers']} spare)")
        else:
            print("❌ No suitable chiller configurations found.")
    
    except Exception as e:
        print(f"❌ Chiller analysis error: {e}")


def show_web_interface_help():
    """Show information about the V2 web interface."""
    print("\n🌐 V2 WEB INTERFACE")
    print("="*50)
    print("For advanced features and interactive charts, use the V2 web interface:")
    print()
    print("🚀 START WEB INTERFACE:")
    print("   python gradio_app.py")
    print()
    print("📊 WEB-ONLY FEATURES:")
    print("   • Interactive Plotly charts")
    print("   • Layout heatmaps with riser placement")
    print("   • Editable per-hall MW DataFrames")
    print("   • Riser stack bar charts")
    print("   • Export results and charts")
    print()
    print("☁️  CLOUD DEPLOYMENT:")
    print("   • Ready for Render.com deployment")
    print("   • Automatic port binding ($PORT)")
    print("   • Professional UI with responsive design")
    print()
    print("📖 See README.md for complete deployment instructions.")


def main_calculator():
    """Main calculator flow control."""
    display_welcome()
    
    while True:
        choice = get_menu_choice()
        
        if choice == 1:
            run_quick_sizing()
        elif choice == 2:
            run_layout_analysis()
        elif choice == 3:
            show_web_interface_help()
        elif choice == 4:
            print("\n👋 Thank you for using Data Center Pipe Sizer V2!")
            sys.exit(0)
        
        # Ask if user wants to continue
        if input("\nRun another calculation? [Y/n]: ").lower() in ['n', 'no']:
            print("\n👋 Thank you for using Data Center Pipe Sizer V2!")
            break


if __name__ == "__main__":
    try:
        main_calculator()
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Please report this issue with your input parameters.")
        sys.exit(1)
