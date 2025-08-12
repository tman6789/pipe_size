#!/usr/bin/env python3
"""
Data Center Pipe Sizer V2 Enhanced - CLI Calculator

Enhanced Features:
- Advanced riser modeling with proper counts
- Per-floor reduction with downstream load sequencing
- Comprehensive cooling load math (IT + Fan% + Misc)
- Enhanced hall load tables
- Advanced velocity warnings and edge case handling
- Riser reduction schedule for diameter stepping
- Integrated chiller sizing with tons conversion

Run locally:
  python main_enhanced.py
"""

import math
import os
import sys
import pandas as pd
from typing import Dict, List, Optional, Tuple
from calc.pipe_lookup import get_nominal_pipe_size, get_pipe_id
from calc.fluid_properties import get_fluid_options, get_fluid_properties, get_fluid_name
from calc.flow import mw_to_gpm
from calc.layout import (
    parse_layout, make_hall_names, column_aggregates, 
    create_hall_dataframe, validate_hall_data,
    get_layout_stats, calculate_riser_count,
    build_hall_table, calculate_riser_reduction_schedule,
    get_column_summary
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
    """Display welcome message and enhanced V2 features."""
    print("="*80)
    print("🏢 DATA CENTER PIPE SIZER V2 ENHANCED")
    print("="*80)
    print("Professional chilled-water piping and chiller sizing tool with advanced features")
    print("\n🔥 ENHANCED V2 FEATURES:")
    print("• Advanced riser modeling: shared = 2×(C+R), unshared = 4×(C+R)")
    print("• Per-floor reduction with downstream load sequencing")
    print("• Comprehensive cooling load math (IT + Fan% + Misc per-hall/building)")
    print("• Enhanced hall load tables with position tracking")
    print("• Advanced velocity warnings and edge case handling")
    print("• Riser reduction schedule for diameter stepping")
    print("• Integrated chiller sizing with tons conversion")
    print("="*80)


def get_menu_choice() -> int:
    """Get main menu selection from user."""
    print("\n🔧 ENHANCED CALCULATION OPTIONS:")
    print("1. Quick Sizing (Simple MW + ΔT)")
    print("2. Enhanced Layout Analysis (Advanced with Per-Floor Reduction)")
    print("3. Enhanced V2 Web Interface Help")
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


def get_enhanced_layout_inputs() -> Dict:
    """Get enhanced layout-based inputs for advanced mode."""
    print("\n🏗️ ENHANCED LAYOUT CONFIGURATION:")
    
    # Get layout specification
    while True:
        layout_str = input("Data center layout (C×R×F, e.g. 4×3×2): ").strip()
        try:
            columns, rows, floors = parse_layout(layout_str)
            total_halls = columns * rows * floors
            
            # Calculate riser counts
            shared_risers_count = calculate_riser_count(columns, rows, True)
            unshared_risers_count = calculate_riser_count(columns, rows, False)
            
            print(f"✅ Layout: {columns} columns × {rows} rows × {floors} floors = {total_halls} halls")
            print(f"   Risers: {shared_risers_count} shared, {unshared_risers_count} unshared")
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
    
    # Enhanced load inputs
    while True:
        try:
            fan_heat_pct = float(input("Fan heat percentage (0-20%) [default 5]: ") or 5)
            if 0 <= fan_heat_pct <= 20:
                break
            print("Fan heat should be between 0-20%.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            misc_load_mw = float(input("Miscellaneous load (MW) [default 0]: ") or 0)
            if misc_load_mw >= 0:
                break
            print("Misc load must be non-negative.")
        except ValueError:
            print("Please enter a valid number.")
    
    if misc_load_mw > 0:
        misc_per_hall = input("Apply misc load per-hall? [Y/n]: ").lower() not in ['n', 'no']
    else:
        misc_per_hall = True
    
    # Basic sizing parameters
    basic_params = get_basic_inputs()
    
    # Riser configuration
    shared_risers = input("\n🏗️ Use shared risers among halls? [Y/n]: ").lower() not in ['n', 'no']
    
    # Build comprehensive hall table
    hall_table = build_hall_table(
        columns=columns,
        rows=rows,
        floors=floors,
        it_mw_data=hall_loads,
        fan_percent=fan_heat_pct,
        misc_load_mw=misc_load_mw,
        misc_per_hall=misc_per_hall,
        include_floors=include_floors
    )
    
    total_it_mw = hall_table['IT_MW'].sum()
    total_cooling_mw = hall_table['Total_Cooling_MW'].sum()
    
    return {
        **basic_params,
        'layout': (columns, rows, floors),
        'include_floors': include_floors,
        'hall_loads': hall_loads,
        'hall_table': hall_table,
        'fan_heat_pct': fan_heat_pct,
        'misc_load_mw': misc_load_mw,
        'misc_per_hall': misc_per_hall,
        'shared_risers': shared_risers,
        'shared_risers_count': shared_risers_count,
        'unshared_risers_count': unshared_risers_count,
        'total_it_mw': total_it_mw,
        'total_cooling_mw': total_cooling_mw
    }


def run_quick_sizing():
    """Run quick sizing mode with enhanced features."""
    print("\n🚀 QUICK SIZING MODE (Enhanced)")
    
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
    print("\n" + "="*60)
    print("📊 ENHANCED QUICK SIZING RESULTS")
    print("="*60)
    print(f"Total Load: {inputs['mw']} MW")
    print(f"Total Flow: {total_gpm:,.0f} GPM")
    print(f"ΔT: {inputs['delta_t']}°F")
    print(f"Fluid: {get_fluid_name(fluid_type)}")
    
    print("\n🔧 Main Distribution Pipe:")
    for key, value in result.items():
        if "Pressure Drop" in key:
            print(f"ΔP/100ft (psi): {value}")
        else:
            print(f"{key}: {value}")
    
    # Enhanced velocity and system warnings
    velocity = result.get('Velocity (ft/s)', 0)
    warnings = []
    
    if velocity > 10:
        warnings.append(f"⚠️ Velocity {velocity} ft/s exceeds 10 ft/s - consider larger diameter")
    elif velocity < 3:
        warnings.append(f"ℹ️ Velocity {velocity} ft/s is low - may affect heat transfer")
    
    if total_gpm > 50000:
        warnings.append(f"⚠️ Very large flow rate {total_gpm:,.0f} GPM - verify system capabilities")
    elif total_gpm < 100:
        warnings.append(f"ℹ️ Small flow rate {total_gpm:.0f} GPM - consider minimum requirements")
    
    if warnings:
        print("\n⚠️ SYSTEM ANALYSIS:")
        for warning in warnings:
            print(f"   {warning}")
    
    # Simple chiller sizing
    print("\n❄️ CHILLER RECOMMENDATIONS:")
    run_chiller_analysis(inputs['mw'])


def run_enhanced_layout_analysis():
    """Run enhanced layout-based analysis with per-floor reduction."""
    print("\n🏗️ ENHANCED LAYOUT ANALYSIS MODE")
    
    # Get inputs
    inputs = get_enhanced_layout_inputs()
    fluid_type, density, viscosity = get_fluid_selection()
    
    columns, rows, floors = inputs['layout']
    hall_table = inputs['hall_table']
    
    print("\n" + "="*70)
    print("📊 ENHANCED LAYOUT ANALYSIS RESULTS")
    print("="*70)
    print(f"Layout: {columns}×{rows}×{floors} ({len(hall_table)} halls)")
    print(f"Total IT Load: {inputs['total_it_mw']:.1f} MW")
    print(f"Fan Load: {inputs['total_it_mw'] * inputs['fan_heat_pct'] / 100:.1f} MW ({inputs['fan_heat_pct']}%)")
    print(f"Misc Load: {inputs['misc_load_mw']:.1f} MW ({'per-hall' if inputs['misc_per_hall'] else 'building total'})")
    print(f"Total Cooling Load: {inputs['total_cooling_mw']:.1f} MW")
    print(f"Total Flow: {mw_to_gpm(inputs['total_cooling_mw'], inputs['delta_t']):,.0f} GPM")
    print(f"Riser Count: {inputs['shared_risers_count'] if inputs['shared_risers'] else inputs['unshared_risers_count']} ({'shared' if inputs['shared_risers'] else 'unshared'})")
    
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
            print(f"ΔP/100ft (psi): {value}")
        else:
            print(f"{key}: {value}")
    
    # Enhanced riser analysis with per-floor reduction
    if inputs['shared_risers']:
        print("\n🏗️ SHARED RISER ANALYSIS (Enhanced with Per-Floor Reduction):")
        
        # Get column summary
        column_summary = get_column_summary(hall_table)
        
        if not column_summary.empty:
            print(f"\n{'Column':<8} {'IT MW':<8} {'Fan MW':<8} {'Misc MW':<9} {'Total MW':<10} {'GPM':<8} {'Pipe Size':<12} {'Velocity':<10} {'ΔP/100ft'}")
            print("-" * 90)
            
            warnings = []
            for _, row in column_summary.iterrows():
                col_total_mw = row['Total_Cooling_MW']
                col_gpm = mw_to_gpm(col_total_mw, inputs['delta_t'])
                
                # Size riser for this column (at base/highest load)
                col_btu_hr = col_total_mw * 3.412e6
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
                
                print(f"{row['Column']:<8} {row['Total_IT_MW']:<8.1f} {row['Total_Fan_MW']:<8.1f} {row['Total_Misc_MW']:<9.1f} {col_total_mw:<10.1f} {col_gpm:<8.0f} {pipe_size:<12} {velocity:<10.1f} {dp_psi}")
                
                if velocity > 10:
                    warnings.append(f"Column {row['Column']}: velocity {velocity:.1f} ft/s > 10 ft/s")
                elif velocity < 3:
                    warnings.append(f"Column {row['Column']}: velocity {velocity:.1f} ft/s is low")
            
            # Show per-floor reduction schedule
            if floors > 1:
                print("\n📋 RISER REDUCTION SCHEDULE (Per Floor):")
                reduction_schedule = calculate_riser_reduction_schedule(hall_table, columns, rows, floors)
                
                if not reduction_schedule.empty:
                    print(f"{'Column':<8} {'Floor':<6} {'Floor Load':<12} {'Cumulative':<12} {'Remaining':<12}")
                    print(f"{'      ':<8} {'     ':<6} {'(MW)':<12} {'(MW)':<12} {'(MW)':<12}")
                    print("-" * 60)
                    
                    for _, sched_row in reduction_schedule.iterrows():
                        print(f"{sched_row['Column']:<8} {sched_row['Floor']:<6} {sched_row['Floor_Load_MW']:<12.1f} "
                              f"{sched_row['Cumulative_Load_MW']:<12.1f} {sched_row['Remaining_Load_MW']:<12.1f}")
                    
                    print("\nℹ️  Remaining Load = Load still carried by riser at this floor level")
                    print("   Use this for riser diameter stepping calculations")
            
            if warnings:
                print("\n⚠️ VELOCITY WARNINGS:")
                for warning in warnings:
                    print(f"   {warning}")
    
    else:
        print(f"\n🏠 INDIVIDUAL HALL ANALYSIS (Unshared Risers):")
        print(f"Large layout with {len(hall_table)} halls - use Web Interface for detailed per-hall analysis")
        print(f"Summary: {inputs['unshared_risers_count']} individual riser connections required")
    
    # Enhanced chiller sizing
    print("\n❄️ ENHANCED CHILLER RECOMMENDATIONS:")
    run_chiller_analysis(inputs['total_cooling_mw'])
    
    # System summary
    print("\n📋 SYSTEM SUMMARY:")
    print(f"• Total Halls: {len(hall_table)}")
    print(f"• Riser Strategy: {'Shared by column' if inputs['shared_risers'] else 'Individual per hall'}")
    print(f"• Total Risers: {inputs['shared_risers_count'] if inputs['shared_risers'] else inputs['unshared_risers_count']}")
    print(f"• Main Distribution: {mw_to_gpm(inputs['total_cooling_mw'], inputs['delta_t']):,.0f} GPM")
    if inputs['misc_load_mw'] > 0:
        print(f"• Miscellaneous Loads: {inputs['misc_load_mw']:.1f} MW ({'per-hall' if inputs['misc_per_hall'] else 'building'})")
    
    print("\nℹ️  For interactive charts and detailed analysis, use: python gradio_app.py")


def run_chiller_analysis(cooling_mw: float):
    """Run enhanced chiller analysis and display results."""
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
            print(f"   Equivalent: {best['chiller_size_mw']/0.003517:.0f} tons per chiller")
        else:
            print("❌ No suitable chiller configurations found.")
    
    except Exception as e:
        print(f"❌ Chiller analysis error: {e}")


def show_enhanced_web_interface_help():
    """Show information about the enhanced V2 web interface."""
    print("\n🌐 ENHANCED V2 WEB INTERFACE")
    print("="*60)
    print("For advanced features and interactive analysis, use the enhanced web interface:")
    print()
    print("🚀 START ENHANCED WEB INTERFACE:")
    print("   python gradio_app.py")
    print()
    print("🔥 NEW ENHANCED FEATURES:")
    print("   • Riser count calculations: 2×(C+R) shared, 4×(C+R) unshared")
    print("   • Per-floor reduction schedules with load stepping")
    print("   • Enhanced cooling load math (IT + Fan% + Misc)")
    print("   • Comprehensive hall load tables")
    print("   • Miscellaneous loads (per-hall or building total)")
    print("   • Advanced velocity warnings and edge case handling")
    print()
    print("📊 INTERACTIVE FEATURES:")
    print("   • Interactive Plotly charts (velocity, ΔP, layout heatmap)")
    print("   • Riser stack bar charts with load analysis")
    print("   • Conditional per-hall MW DataFrames")
    print("   • Real-time riser reduction schedule display")
    print("   • Enhanced chiller sizing with tons conversion")
    print()
    print("📋 COMPREHENSIVE OUTPUTS:")
    print("   • Main plant pipe sizing")
    print("   • Hall load summary (IT/Fan/Misc breakdown)")
    print("   • Riser analysis by column")
    print("   • Per-floor reduction schedule")
    print("   • Top-3 chiller configurations")
    print("   • 4 interactive Plotly charts")
    print()
    print("☁️ CLOUD DEPLOYMENT READY:")
    print("   • Enhanced Render.com compatibility")
    print("   • Matplotlib Agg backend for headless operation")
    print("   • Robust error handling and edge case management")
    print("   • Professional responsive UI")
    print()
    print("📖 See README.md for complete deployment instructions and examples.")


def main_enhanced_calculator():
    """Enhanced main calculator flow control."""
    display_welcome()
    
    while True:
        choice = get_menu_choice()
        
        try:
            if choice == 1:
                run_quick_sizing()
            elif choice == 2:
                run_enhanced_layout_analysis()
            elif choice == 3:
                show_enhanced_web_interface_help()
            elif choice == 4:
                print("\n👋 Thank you for using Data Center Pipe Sizer V2 Enhanced!")
                sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error during calculation: {e}")
            print("Please check your inputs and try again.")
            continue
        
        # Ask if user wants to continue
        try:
            continue_choice = input("\nRun another calculation? [Y/n]: ").lower()
            if continue_choice in ['n', 'no']:
                print("\n👋 Thank you for using Data Center Pipe Sizer V2 Enhanced!")
                break
        except KeyboardInterrupt:
            print("\n\n👋 Thank you for using Data Center Pipe Sizer V2 Enhanced!")
            break


if __name__ == "__main__":
    try:
        main_enhanced_calculator()
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user.")
        print("👋 Thank you for using Data Center Pipe Sizer V2 Enhanced!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error in enhanced calculator: {e}")
        print("Please report this issue with your input parameters.")
        print("For stable operation, try the web interface: python gradio_app.py")
        sys.exit(1)