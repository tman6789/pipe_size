#!/usr/bin/env python3
"""
V2 Gradio web app for the Data Center Pipe Sizer.

V2 Features:
- Layout-based sizing with C×R×F format
- Per-hall MW inputs with editable DataFrame 
- Riser sharing analysis
- Plotly interactive charts
- Enhanced chiller sizing with tons
- Velocity warnings and ΔP normalization

Run locally:
  python gradio_app.py

Run with a public share link:
  python gradio_app.py --share
"""
import argparse
import pandas as pd
import gradio as gr
import os
from typing import Optional, Dict, List, Tuple

# Import existing logic
from main import pipeline_sizing
from chiller_sizing import advanced_chiller_sizing, ChillerStrategy, RedundancyModel
from calc.fluid_properties import (
    get_fluid_options,
    get_fluid_properties,
    get_fluid_name,
)
from calc.flow import mw_to_gpm
from calc.layout import (
    parse_layout, 
    make_hall_names, 
    column_aggregates, 
    create_hall_dataframe, 
    validate_hall_data,
    get_layout_stats
)
from calc.visualization import (
    velocity_figure,
    dp_figure,
    layout_heatmap,
    riser_stack_bar
)

def compute_v2_results(
    # Layout inputs
    layout_str: str,
    include_floors: bool,
    use_same_mw: bool,
    single_total_mw: float,
    hall_data: pd.DataFrame,
    fan_heat_pct: float,
    # Riser inputs  
    shared_risers: bool,
    riser_placement: str,
    # Fluid & sizing inputs
    delta_t_f: float,
    target_velocity_fps: float, 
    fluid_choice_idx: int,
    max_dp_psi: float,
    # Chiller inputs
    redundancy_model_name: str,
    redundancy_percent: float,
    strategy_name: str,
    max_chillers: int,
    electricity_rate: float
) -> Tuple:
    """V2 compute function with layout-based sizing and enhanced features."""
    
    # Resolve fluid properties
    fluid_options = get_fluid_options()
    fluid_choice_idx = max(0, min(fluid_choice_idx, len(fluid_options)-1))
    fluid_key = fluid_options[fluid_choice_idx]
    density, viscosity = get_fluid_properties(fluid_key)
    fluid_label = get_fluid_name(fluid_key)
    
    warnings = []
    
    # Parse layout if provided
    total_mw = single_total_mw
    hall_loads_dict = {}
    layout_stats = {}
    
    if layout_str and layout_str.strip():
        try:
            columns, rows, floors = parse_layout(layout_str)
            layout_stats = get_layout_stats(layout_str, include_floors)
            
            if use_same_mw:
                # Use single MW for all halls 
                hall_names = make_hall_names(columns, rows, floors, include_floors)
                halls_per_hall = single_total_mw / len(hall_names) if hall_names else 0
                hall_loads_dict = {name: halls_per_hall for name in hall_names}
                total_mw = single_total_mw
            else:
                # Use per-hall MW from DataFrame
                if not hall_data.empty and 'Hall' in hall_data.columns and 'IT Load (MW)' in hall_data.columns:
                    hall_loads_dict = dict(zip(hall_data['Hall'], hall_data['IT Load (MW)']))
                    total_mw = hall_data['IT Load (MW)'].sum()
        except ValueError as e:
            warnings.append(f"Layout parsing error: {e}")
    
    # Apply fan heat factor to get cooling MW
    cooling_mw = total_mw * (1 + fan_heat_pct / 100)
    
    # MW → BTU/hr → lb/hr (Cp≈1.0 BTU/lb°F)
    btu_hr = cooling_mw * 3.412e6
    mass_flow_rate = btu_hr / (delta_t_f * 1.0)
    
    # Main pipe sizing
    main_result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=density,
        viscosity=viscosity,
        max_pressure_drop=max_dp_psi * 144,  # psi → lb/ft²
        max_velocity=target_velocity_fps,
    )
    
    # Normalize ΔP to per 100 ft
    if "Pressure Drop (psi)" in main_result:
        main_result["ΔP (psi/100ft)"] = main_result["Pressure Drop (psi)"]
        del main_result["Pressure Drop (psi)"]
    
    # Check for high velocity warnings
    if "Velocity (ft/s)" in main_result:
        if main_result["Velocity (ft/s)"] > 10:
            warnings.append("⚠️ Main pipe velocity exceeds 10 ft/s - consider larger diameter")
    
    main_df = pd.DataFrame([main_result])
    
    # Riser/Hall analysis
    riser_df = pd.DataFrame()
    hall_df = pd.DataFrame()
    
    if layout_str and hall_loads_dict:
        try:
            columns, rows, floors = parse_layout(layout_str)
            
            if shared_risers:
                # Shared risers - aggregate by column
                hall_data_for_agg = pd.DataFrame([
                    {"Hall": hall, "IT Load (MW)": it_mw} 
                    for hall, it_mw in hall_loads_dict.items()
                ])
                
                column_agg = column_aggregates(hall_data_for_agg, columns, rows, floors, include_floors)
                
                if not column_agg.empty:
                    riser_results = []
                    for _, row in column_agg.iterrows():
                        col_it_mw = row['Total_MW']
                        col_cooling_mw = col_it_mw * (1 + fan_heat_pct / 100)
                        col_gpm = mw_to_gpm(col_cooling_mw, delta_t_f)
                        
                        # Size this column's riser
                        col_btu_hr = col_cooling_mw * 3.412e6
                        col_mass_flow = col_btu_hr / (delta_t_f * 1.0)
                        
                        col_result = pipeline_sizing(
                            mass_flow_rate=col_mass_flow,
                            density=density,
                            viscosity=viscosity,
                            max_pressure_drop=max_dp_psi * 144,
                            max_velocity=target_velocity_fps,
                        )
                        
                        # Extract key metrics
                        nominal = col_result.get('Standard Pipe Size', col_result.get('Pipe Diameter (in)', 'N/A'))
                        velocity = col_result.get('Velocity (ft/s)', 0)
                        dp_psi = col_result.get('Pressure Drop (psi)', col_result.get('ΔP (psi/100ft)', 0))
                        
                        if velocity > 10:
                            warnings.append(f"⚠️ Column {row['Column']} riser velocity {velocity:.1f} ft/s exceeds 10 ft/s")
                        
                        riser_results.append({
                            'Column': row['Column'],
                            'Total_MW': col_it_mw,
                            'Cooling_MW': col_cooling_mw,
                            'GPM': col_gpm,
                            'Nominal': nominal,
                            'Velocity': velocity,
                            'ΔP/100ft': dp_psi
                        })
                    
                    riser_df = pd.DataFrame(riser_results)
            else:
                # Individual hall sizing
                hall_results = []
                for hall, it_mw in hall_loads_dict.items():
                    if it_mw > 0:
                        hall_cooling_mw = it_mw * (1 + fan_heat_pct / 100)
                        hall_gpm = mw_to_gpm(hall_cooling_mw, delta_t_f)
                        
                        hall_btu_hr = hall_cooling_mw * 3.412e6
                        hall_mass_flow = hall_btu_hr / (delta_t_f * 1.0)
                        
                        hall_result = pipeline_sizing(
                            mass_flow_rate=hall_mass_flow,
                            density=density,
                            viscosity=viscosity,
                            max_pressure_drop=max_dp_psi * 144,
                            max_velocity=target_velocity_fps,
                        )
                        
                        nominal = hall_result.get('Standard Pipe Size', hall_result.get('Pipe Diameter (in)', 'N/A'))
                        velocity = hall_result.get('Velocity (ft/s)', 0)
                        dp_psi = hall_result.get('Pressure Drop (psi)', hall_result.get('ΔP (psi/100ft)', 0))
                        
                        if velocity > 10:
                            warnings.append(f"⚠️ Hall {hall} velocity {velocity:.1f} ft/s exceeds 10 ft/s")
                        
                        hall_results.append({
                            'Hall': hall,
                            'IT_MW': it_mw,
                            'Cooling_MW': hall_cooling_mw,
                            'GPM': hall_gpm,
                            'Nominal': nominal,
                            'Velocity': velocity,
                            'ΔP/100ft': dp_psi
                        })
                
                hall_df = pd.DataFrame(hall_results)
                        
        except Exception as e:
            warnings.append(f"Riser analysis error: {e}")
    
    # Enhanced chiller sizing with tons
    redundancy_map = {
        "N+1": RedundancyModel.N_PLUS_1,
        "N+2": RedundancyModel.N_PLUS_2,
        "N+%": RedundancyModel.N_PLUS_PERCENT,
    }
    strategy_map = {
        "Balanced": ChillerStrategy.BALANCED,
        "Modular": ChillerStrategy.MODULAR,
        "Central": ChillerStrategy.CENTRAL,
    }
    redundancy_model = redundancy_map.get(redundancy_model_name, RedundancyModel.N_PLUS_1)
    strategy = strategy_map.get(strategy_name, ChillerStrategy.BALANCED)
    
    chiller_results = advanced_chiller_sizing(
        total_mw=cooling_mw,  # Use cooling MW for chiller sizing
        redundancy_model=redundancy_model,
        redundancy_percent=redundancy_percent,
        strategy=strategy,
        max_chillers=max_chillers,
        electricity_rate=electricity_rate,
    )
    
    chiller_df_pretty = pd.DataFrame()
    if chiller_results:
        top3 = chiller_results[:3]
        chiller_df = pd.DataFrame(top3)
        
        # Add tons column (1 ton ≈ 0.003517 MW, so MW/0.003517 = tons)
        if 'chiller_size_mw' in chiller_df.columns:
            chiller_df['chiller_size_tons'] = chiller_df['chiller_size_mw'] / 0.003517
        
        # Pretty formatting
        display_cols = [
            ("chiller_size_mw", "Chiller MW"),
            ("chiller_size_tons", "Chiller Tons"), 
            ("total_chillers", "Total Units"),
            ("operating_chillers", "Operating"),
            ("redundant_chillers", "Redundant"),
            ("loading_percent", "Loading %"),
            ("redundancy_percent", "Redundancy %"),
            ("ten_year_tco", "10-Yr TCO ($)"),
            ("tco_per_mw", "TCO/MW ($/MW)"),
            ("annual_energy_cost", "Annual Energy ($)"),
        ]
        
        cols_present = [c for c, _ in display_cols if c in chiller_df.columns]
        out_df = chiller_df[cols_present].copy()
        rename_map = {c: label for c, label in display_cols if c in out_df.columns}
        out_df = out_df.rename(columns=rename_map)
        
        # Format columns
        for col in ["10-Yr TCO ($)", "TCO/MW ($/MW)", "Annual Energy ($)"]:
            if col in out_df.columns:
                out_df[col] = out_df[col].apply(lambda x: f"${x:,.0f}")
        if "Loading %" in out_df.columns:
            out_df["Loading %"] = out_df["Loading %"].apply(lambda x: f"{x:.1f}%")
        if "Redundancy %" in out_df.columns:
            out_df["Redundancy %"] = out_df["Redundancy %"].apply(lambda x: f"{x:.1f}%")
        if "Chiller Tons" in out_df.columns:
            out_df["Chiller Tons"] = out_df["Chiller Tons"].apply(lambda x: f"{x:.0f}")
        if "Chiller MW" in out_df.columns:
            out_df["Chiller MW"] = out_df["Chiller MW"].apply(lambda x: f"{x:.1f}")
        
        chiller_df_pretty = out_df
    
    # Generate summary
    total_gpm = mw_to_gpm(cooling_mw, delta_t_f)
    
    summary_parts = [
        "### V2 Analysis Summary",
        f"- **IT Load**: {total_mw:.1f} MW",
        f"- **Cooling Load**: {cooling_mw:.1f} MW (includes {fan_heat_pct}% fan heat)",
        f"- **Total Flow**: {total_gpm:,.0f} GPM",
        f"- **ΔT**: {delta_t_f}°F", 
        f"- **Target Velocity**: {target_velocity_fps} ft/s",
        f"- **Fluid**: {fluid_label}",
        f"- **Max ΔP**: {max_dp_psi} psi/100ft"
    ]
    
    if layout_str:
        summary_parts.append(f"- **Layout**: {layout_str} ({layout_stats.get('total_halls', 0)} halls)")
        summary_parts.append(f"- **Riser Strategy**: {'Shared by column' if shared_risers else 'Individual halls'}")
    
    if warnings:
        summary_parts.append("\n### ⚠️ Warnings")
        for warning in warnings:
            summary_parts.append(f"- {warning}")
    
    summary_md = "\n".join(summary_parts)
    
    # Generate charts
    vel_fig = velocity_figure(total_gpm, delta_t_f, 15.0)
    dp_fig = dp_figure(target_velocity_fps, density, viscosity, delta_t_f)
    
    layout_fig = None
    riser_fig = None
    
    if layout_str and hall_loads_dict:
        try:
            columns, rows, floors = parse_layout(layout_str)
            layout_fig = layout_heatmap(columns, rows, floors, hall_loads_dict, riser_placement, include_floors)
        except:
            pass
    
    if not riser_df.empty:
        riser_fig = riser_stack_bar(riser_df)
    
    return (
        summary_md, 
        main_df, 
        riser_df if not riser_df.empty else hall_df, 
        chiller_df_pretty,
        vel_fig,
        dp_fig, 
        layout_fig,
        riser_fig
    )


def update_hall_dataframe(layout_str: str, include_floors: bool, default_mw: float) -> pd.DataFrame:
    """Update the hall DataFrame when layout changes."""
    if not layout_str or not layout_str.strip():
        return pd.DataFrame(columns=['Hall', 'IT Load (MW)'])
    
    try:
        return create_hall_dataframe(layout_str, include_floors, default_mw)
    except:
        return pd.DataFrame(columns=['Hall', 'IT Load (MW)'])


def build_v2_interface(port: int, share: bool = False):
    """Build V2 interface with layout inputs and enhanced features."""
    fluid_names = [get_fluid_name(f) for f in get_fluid_options()]

    with gr.Blocks(title="Data Center Pipe Sizer V2", theme=gr.themes.Default()) as demo:
        gr.Markdown("# 🏢 Data Center Pipe Sizer V2")
        gr.Markdown(
            "Professional pipe sizing and chiller selection for data center cooling systems.\n"
            "**New in V2:** Layout-based sizing, per-hall loads, riser sharing, interactive Plotly charts."
        )

        with gr.Row():
            # Left column - Inputs
            with gr.Column(scale=1):
                gr.Markdown("## 📐 Layout Configuration")
                
                layout_input = gr.Textbox(
                    label="Data Center Layout (C×R×F)", 
                    placeholder="e.g. 4×3×2 (4 cols, 3 rows, 2 floors)",
                    value="4×3×1"
                )
                
                include_floors = gr.Checkbox(
                    label="Include floor numbers in hall names", 
                    value=True
                )
                
                use_same_mw = gr.Checkbox(
                    label="Use same MW for all halls", 
                    value=True
                )
                
                single_total_mw = gr.Number(
                    label="Total IT Load (MW)", 
                    value=50.0, 
                    visible=True
                )
                
                fan_heat_pct = gr.Slider(
                    minimum=0, maximum=20, step=1, value=5,
                    label="Fan Heat % (added to cooling load)"
                )
                
                # Hall-specific MW input (initially hidden)
                hall_dataframe = gr.Dataframe(
                    headers=["Hall", "IT Load (MW)"],
                    datatype=["str", "number"],
                    interactive=True,
                    visible=False,
                    label="Per-Hall IT Loads (MW)"
                )
                
                gr.Markdown("## 🏗️ Riser Configuration")
                
                shared_risers = gr.Checkbox(
                    label="Shared risers among halls?", 
                    value=True
                )
                
                riser_placement = gr.Dropdown(
                    choices=["corners", "edges", "center"],
                    value="corners", 
                    label="Riser Placement (visualization only)"
                )
                
                gr.Markdown("## ⚙️ Fluid & Sizing")
                
                delta_t = gr.Number(label="ΔT (°F)", value=15.0)
                velocity = gr.Number(label="Target Velocity (ft/s)", value=12.0)
                fluid = gr.Dropdown(choices=fluid_names, value=fluid_names[0], label="Fluid Type")
                max_dp = gr.Number(label="Max Pressure Drop (psi/100ft)", value=20.0)
                
                gr.Markdown("## 🥶 Chiller Settings")
                
                redundancy = gr.Dropdown(
                    choices=["N+1", "N+2", "N+%"], 
                    value="N+1", 
                    label="Redundancy Model"
                )
                redundancy_pct = gr.Slider(
                    minimum=10, maximum=50, step=5, value=20, 
                    label="Redundancy % (for N+%)"
                )
                strategy = gr.Dropdown(
                    choices=["Balanced", "Modular", "Central"], 
                    value="Balanced", 
                    label="Chiller Strategy"
                )
                max_units = gr.Slider(
                    minimum=2, maximum=50, step=1, value=20, 
                    label="Max Number of Chillers"
                )
                elec_rate = gr.Number(label="Electricity Rate ($/kWh)", value=0.12)

                run_btn = gr.Button("🚀 Run V2 Analysis", variant="primary", size="lg")

            # Right column - Outputs
            with gr.Column(scale=2):
                summary = gr.Markdown()
                
                with gr.Row():
                    with gr.Column():
                        main_table = gr.Dataframe(label="Main Distribution Pipe", interactive=False)
                        riser_table = gr.Dataframe(label="Riser/Hall Analysis", interactive=False)
                    with gr.Column():
                        chiller_table = gr.Dataframe(label="Top 3 Chiller Options", interactive=False)
                
                gr.Markdown("## 📊 Interactive Charts")
                
                with gr.Row():
                    velocity_chart = gr.Plot(label="Velocity vs Diameter")
                    dp_chart = gr.Plot(label="Pressure Drop vs Diameter")
                
                with gr.Row():
                    layout_chart = gr.Plot(label="Data Center Layout")
                    riser_chart = gr.Plot(label="Riser Stack Analysis")

        # Event handlers
        def toggle_mw_input(use_same):
            return {
                single_total_mw: gr.update(visible=use_same),
                hall_dataframe: gr.update(visible=not use_same)
            }
        
        def update_halls_df(layout_str, include_floors, use_same):
            if use_same or not layout_str.strip():
                return gr.update(value=pd.DataFrame(columns=['Hall', 'IT Load (MW)']), visible=not use_same)
            
            df = update_hall_dataframe(layout_str, include_floors, 1.0)
            return gr.update(value=df, visible=not use_same)
        
        use_same_mw.change(
            fn=toggle_mw_input,
            inputs=[use_same_mw],
            outputs=[single_total_mw, hall_dataframe]
        )
        
        layout_input.change(
            fn=update_halls_df,
            inputs=[layout_input, include_floors, use_same_mw],
            outputs=[hall_dataframe]
        )
        
        include_floors.change(
            fn=update_halls_df,
            inputs=[layout_input, include_floors, use_same_mw], 
            outputs=[hall_dataframe]
        )

        def _on_run_v2(
            layout_str, include_floors, use_same_mw, single_total_mw, hall_data,
            fan_heat_pct, shared_risers, riser_placement, delta_t, velocity, 
            fluid_name, max_dp, redundancy, redundancy_pct, strategy, max_units, elec_rate
        ):
            # Convert hall_data to DataFrame if it's not already
            if not isinstance(hall_data, pd.DataFrame):
                hall_data = pd.DataFrame(hall_data, columns=['Hall', 'IT Load (MW)'])
            
            # Resolve fluid index
            fluids = [get_fluid_name(f) for f in get_fluid_options()]
            try:
                fluid_idx = fluids.index(fluid_name)
            except ValueError:
                fluid_idx = 0

            return compute_v2_results(
                layout_str=layout_str,
                include_floors=include_floors,
                use_same_mw=use_same_mw,
                single_total_mw=single_total_mw,
                hall_data=hall_data,
                fan_heat_pct=fan_heat_pct,
                shared_risers=shared_risers,
                riser_placement=riser_placement,
                delta_t_f=delta_t,
                target_velocity_fps=velocity,
                fluid_choice_idx=fluid_idx,
                max_dp_psi=max_dp,
                redundancy_model_name=redundancy,
                redundancy_percent=redundancy_pct,
                strategy_name=strategy,
                max_chillers=int(max_units),
                electricity_rate=elec_rate,
            )

        run_btn.click(
            fn=_on_run_v2,
            inputs=[
                layout_input, include_floors, use_same_mw, single_total_mw, hall_dataframe,
                fan_heat_pct, shared_risers, riser_placement, delta_t, velocity,
                fluid, max_dp, redundancy, redundancy_pct, strategy, max_units, elec_rate
            ],
            outputs=[
                summary, main_table, riser_table, chiller_table,
                velocity_chart, dp_chart, layout_chart, riser_chart
            ],
        )

    demo.launch(server_name="0.0.0.0", server_port=port, share=share)


if __name__ == "__main__":
    import argparse, os
    parser = argparse.ArgumentParser(description="Data Center Pipe Sizer V2")
    parser.add_argument("--share", action="store_true", help="Create a public share link")
    args = parser.parse_args()

    port = int(os.getenv("PORT", "7860"))
    print(f"🚀 Starting Data Center Pipe Sizer V2 on port {port}")
    build_v2_interface(port=port, share=args.share)