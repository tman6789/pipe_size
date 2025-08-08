#!/usr/bin/env python3
"""
Gradio web app for the Data Center Pipe Sizer.

Run locally:
  python gradio_app.py

Run with a public share link:
  python gradio_app.py --share
"""
import argparse
import pandas as pd
import gradio as gr

# Import your existing logic
from main import pipeline_sizing
from chiller_sizing import advanced_chiller_sizing, ChillerStrategy, RedundancyModel
from calc.fluid_properties import (
    get_fluid_options,
    get_fluid_properties,
    get_fluid_name,
)

def compute_results(total_mw: float,
                    delta_t_f: float,
                    target_velocity_fps: float,
                    fluid_choice_idx: int,
                    max_dp_psi: float,
                    num_risers: int | None,
                    redundancy_model_name: str,
                    redundancy_percent: float,
                    strategy_name: str,
                    max_chillers: int,
                    electricity_rate: float):
    """Run pipe sizing + (optional) risers + chiller analysis and return tables/markdown."""

    # Resolve fluid
    fluid_options = get_fluid_options()
    fluid_choice_idx = max(0, min(fluid_choice_idx, len(fluid_options)-1))
    fluid_key = fluid_options[fluid_choice_idx]
    density, viscosity = get_fluid_properties(fluid_key)
    fluid_label = get_fluid_name(fluid_key)

    # MW → BTU/hr → lb/hr (Cp≈1.0 BTU/lb°F)
    btu_hr = total_mw * 3.412e6
    mass_flow_rate = btu_hr / (delta_t_f * 1.0)

    # Main pipe
    main_result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=density,
        viscosity=viscosity,
        max_pressure_drop=max_dp_psi * 144,  # psi → lb/ft²
        max_velocity=target_velocity_fps,
    )
    main_df = pd.DataFrame([main_result])

    # Optional risers
    riser_df = pd.DataFrame()
    if num_risers and num_risers > 0:
        per_riser_mass_flow = mass_flow_rate / num_risers
        riser_result = pipeline_sizing(
            mass_flow_rate=per_riser_mass_flow,
            density=density,
            viscosity=viscosity,
            max_pressure_drop=max_dp_psi * 144,
            max_velocity=target_velocity_fps,
        )
        riser_df = pd.DataFrame([riser_result])

    # Chillers
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
        total_mw=total_mw,
        redundancy_model=redundancy_model,
        redundancy_percent=redundancy_percent,
        strategy=strategy,
        max_chillers=max_chillers,
        electricity_rate=electricity_rate,
    )

    if chiller_results:
        top3 = chiller_results[:3]
        chiller_df = pd.DataFrame(top3)

        # Pretty table
        display_cols = [
            ("chiller_size_tons", "Chiller Size (tons)"),
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

        for col in ["10-Yr TCO ($)", "TCO/MW ($/MW)", "Annual Energy ($)"]:
            if col in out_df.columns:
                out_df[col] = out_df[col].apply(lambda x: f"${x:,.0f}")
        if "Loading %" in out_df.columns:
            out_df["Loading %"] = out_df["Loading %"].apply(lambda x: f"{x:.1f}%")
        if "Redundancy %" in out_df.columns:
            out_df["Redundancy %"] = out_df["Redundancy %"].apply(lambda x: f"{x:.1f}%")

        chiller_df_pretty = out_df
    else:
        chiller_df_pretty = pd.DataFrame()

    summary_md = (
        f"### Inputs\n"
        f"- **Total Load**: {total_mw} MW\n"
        f"- **ΔT**: {delta_t_f} °F\n"
        f"- **Target Velocity**: {target_velocity_fps} ft/s\n"
        f"- **Fluid**: {fluid_label} (ρ={density} lb/ft³, μ={viscosity:.2e} lb/ft·s)\n"
        f"- **Max ΔP**: {max_dp_psi} psi / 100 ft\n"
        + (f"- **Risers**: {num_risers}\n" if num_risers else "")
    )

    return summary_md, main_df, riser_df, chiller_df_pretty


def build_interface(share: bool = False):
    fluid_names = [get_fluid_name(f) for f in get_fluid_options()]

    with gr.Blocks(title="Data Center Pipe Sizer") as demo:
        gr.Markdown("# 🏢 Data Center Pipe Sizer — Gradio UI")
        gr.Markdown("Professional pipe sizing and chiller selection for data center cooling systems.")

        with gr.Row():
            with gr.Column():
                total_mw = gr.Number(label="Total Cooling Load (MW)", value=50.0)
                delta_t = gr.Number(label="ΔT (°F)", value=15.0)
                velocity = gr.Number(label="Target Velocity (ft/s)", value=12.0)
                fluid = gr.Dropdown(choices=fluid_names, value=fluid_names[0], label="Fluid Type")
                max_dp = gr.Number(label="Max Pressure Drop (psi per 100 ft)", value=20.0)
                risers = gr.Number(label="Number of Risers (optional)", value=None)

                gr.Markdown("### Chiller Settings")
                redundancy = gr.Dropdown(choices=["N+1", "N+2", "N+%"], value="N+1", label="Redundancy Model")
                redundancy_pct = gr.Slider(minimum=10, maximum=50, step=5, value=20, label="Redundancy % (for N+%)")
                strategy = gr.Dropdown(choices=["Balanced", "Modular", "Central"], value="Balanced", label="Chiller Strategy")
                max_units = gr.Slider(minimum=2, maximum=50, step=1, value=20, label="Max Number of Chillers")
                elec_rate = gr.Number(label="Electricity Rate ($/kWh)", value=0.12)

                run_btn = gr.Button("🚀 Run Sizing", variant="primary")

            with gr.Column():
                summary = gr.Markdown()
                main_table = gr.Dataframe(label="Main Pipe Result", interactive=False)
                riser_table = gr.Dataframe(label="Per-Riser Result", interactive=False)
                chiller_table = gr.Dataframe(label="Top 3 Chiller Options", interactive=False)

        def _on_run(total_mw, delta_t, velocity, fluid_name, max_dp, risers, redundancy, redundancy_pct, strategy, max_units, elec_rate):
            fluids = [get_fluid_name(f) for f in get_fluid_options()]
            try:
                fluid_idx = fluids.index(fluid_name)
            except ValueError:
                fluid_idx = 0

            try:
                risers_int = int(risers) if risers is not None else None
            except Exception:
                risers_int = None

            return compute_results(
                total_mw=total_mw,
                delta_t_f=delta_t,
                target_velocity_fps=velocity,
                fluid_choice_idx=fluid_idx,
                max_dp_psi=max_dp,
                num_risers=risers_int,
                redundancy_model_name=redundancy,
                redundancy_percent=redundancy_pct,
                strategy_name=strategy,
                max_chillers=int(max_units),
                electricity_rate=elec_rate,
            )

        run_btn.click(
            fn=_on_run,
            inputs=[total_mw, delta_t, velocity, fluid, max_dp, risers, redundancy, redundancy_pct, strategy, max_units, elec_rate],
            outputs=[summary, main_table, riser_table, chiller_table],
        )

    demo.launch(share=share)


if __name__ == "__main__":
    import argparse, os
    parser = argparse.ArgumentParser()
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    port = int(os.getenv("PORT", "7860"))
    # IMPORTANT: bind to all interfaces and use the platform port
    build_interface(share=args.share)  # keep the builder
    # and update inside build_interface to:
    # demo.launch(server_name="0.0.0.0", server_port=port, share=False)