#!/usr/bin/env python3
"""
Streamlit web application for Data Center Pipe Sizer.
Provides interactive interface for pipe sizing, chiller selection, and visualization.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import math
import base64

# Import our modules
from calc.fluid_properties import get_fluid_options, get_fluid_properties, get_fluid_name
from chiller_sizing import advanced_chiller_sizing, ChillerStrategy, RedundancyModel
from main import pipeline_sizing

# Page configuration
st.set_page_config(
    page_title="Data Center Pipe Sizer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit application."""
    
    # Header
    st.title("🏢 Data Center Pipe Sizer")
    st.markdown("**Professional pipe sizing and chiller selection for data center cooling systems**")
    st.divider()
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("⚙️ System Parameters")
        
        # Basic inputs
        total_mw = st.number_input(
            "Total Building Cooling Load (MW)",
            min_value=0.1,
            max_value=500.0,
            value=60.0,
            step=0.1,
            help="Total cooling load for the entire data center"
        )
        
        delta_t = st.number_input(
            "ΔT (°F)",
            min_value=5.0,
            max_value=30.0,
            value=15.0,
            step=0.5,
            help="Temperature difference between supply and return water"
        )
        
        target_velocity = st.number_input(
            "Target Velocity (ft/s)",
            min_value=3.0,
            max_value=20.0,
            value=12.0,
            step=0.5,
            help="Desired fluid velocity in pipes"
        )
        
        # Fluid selection
        st.subheader("🌊 Fluid Properties")
        fluid_options = get_fluid_options()
        fluid_names = [get_fluid_name(fluid) for fluid in fluid_options]
        
        selected_fluid_name = st.selectbox(
            "Fluid Type",
            fluid_names,
            index=0,  # Default to water
            help="Select the cooling fluid type"
        )
        
        # Get corresponding fluid type
        selected_fluid = fluid_options[fluid_names.index(selected_fluid_name)]
        density, viscosity = get_fluid_properties(selected_fluid)
        
        # Display fluid properties
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Density", f"{density} lb/ft³")
        with col2:
            st.metric("Viscosity", f"{viscosity:.2e} lb/ft·s")
        
        # Optional parameters
        st.subheader("🔧 Optional Parameters")
        
        max_pressure_drop = st.number_input(
            "Max Pressure Drop (psi)",
            min_value=5.0,
            max_value=50.0,
            value=20.0,
            step=1.0,
            help="Maximum allowable pressure drop"
        )
        
        # Riser configuration
        enable_risers = st.checkbox("Enable Riser Sizing", help="Size individual risers")
        num_risers = None
        if enable_risers:
            num_risers = st.number_input(
                "Number of Risers",
                min_value=1,
                max_value=20,
                value=4,
                step=1,
                help="Number of vertical risers to size"
            )
        
        # Chiller configuration
        st.subheader("❄️ Chiller Configuration")
        
        redundancy_options = {
            "N+1 (One spare chiller)": (RedundancyModel.N_PLUS_1, 0),
            "N+2 (Two spare chillers)": (RedundancyModel.N_PLUS_2, 0),
            "N+% (Percentage redundancy)": (RedundancyModel.N_PLUS_PERCENT, 20)
        }
        
        redundancy_choice = st.selectbox(
            "Redundancy Model",
            list(redundancy_options.keys()),
            help="Select chiller redundancy strategy"
        )
        
        redundancy_model, default_percent = redundancy_options[redundancy_choice]
        
        redundancy_percent = default_percent
        if redundancy_model == RedundancyModel.N_PLUS_PERCENT:
            redundancy_percent = st.slider(
                "Redundancy Percentage (%)",
                min_value=10,
                max_value=50,
                value=20,
                step=5
            )
        
        strategy_options = {
            "Balanced (Medium chillers)": ChillerStrategy.BALANCED,
            "Modular (Many small chillers)": ChillerStrategy.MODULAR,
            "Central (Few large chillers)": ChillerStrategy.CENTRAL
        }
        
        strategy_choice = st.selectbox(
            "Chiller Strategy",
            list(strategy_options.keys()),
            help="Select chiller sizing strategy"
        )
        strategy = strategy_options[strategy_choice]
        
        max_chillers = st.number_input(
            "Max Number of Chillers",
            min_value=2,
            max_value=50,
            value=20,
            step=1
        )
        
        electricity_rate = st.number_input(
            "Electricity Rate ($/kWh)",
            min_value=0.05,
            max_value=0.50,
            value=0.12,
            step=0.01,
            format="%.3f"
        )
        
        # Run button
        st.divider()
        run_sizing = st.button("🚀 Run Sizing Analysis", type="primary", use_container_width=True)
    
    # Main content area
    if run_sizing:
        
        # Calculate pipe sizing
        with st.spinner("Calculating pipe sizes..."):
            
            # Convert MW to mass flow rate
            btu_hr = total_mw * 3.412e6
            mass_flow_rate = btu_hr / (delta_t * 1.0)  # BTU/hr ÷ (ΔT × Cp)
            
            # Main pipe sizing
            main_result = pipeline_sizing(
                mass_flow_rate=mass_flow_rate,
                density=density,
                viscosity=viscosity,
                max_pressure_drop=max_pressure_drop * 144,  # psi to lb/ft²
                max_velocity=target_velocity
            )
            
            # Riser sizing if enabled
            riser_result = None
            if num_risers:
                riser_flow_rate = mass_flow_rate / num_risers
                riser_result = pipeline_sizing(
                    mass_flow_rate=riser_flow_rate,
                    density=density,
                    viscosity=viscosity,
                    max_pressure_drop=max_pressure_drop * 144,
                    max_velocity=target_velocity
                )
        
        # Display pipe sizing results
        st.header("🔧 Pipe Sizing Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Main Distribution Pipe")
            main_df = pd.DataFrame([main_result]).T
            main_df.columns = ["Value"]
            st.dataframe(main_df, use_container_width=True)
        
        with col2:
            if riser_result:
                st.subheader(f"Individual Risers ({num_risers} total)")
                riser_df = pd.DataFrame([riser_result]).T
                riser_df.columns = ["Value"]
                st.dataframe(riser_df, use_container_width=True)
            else:
                st.info("Enable riser sizing in the sidebar to see individual riser calculations.")
        
        # Chiller sizing analysis
        st.header("❄️ Chiller Sizing Analysis")
        
        with st.spinner("Analyzing chiller configurations..."):
            chiller_results = advanced_chiller_sizing(
                total_mw=total_mw,
                redundancy_model=redundancy_model,
                redundancy_percent=redundancy_percent,
                strategy=strategy,
                max_chillers=max_chillers,
                electricity_rate=electricity_rate
            )
        
        if chiller_results:
            # Top 3 configurations
            st.subheader("Top 3 Configurations (by Cost Effectiveness)")
            
            # Prepare data for table
            top_3 = chiller_results[:3]
            chiller_df = pd.DataFrame(top_3)
            
            # Select and rename columns for display
            display_columns = {
                'chiller_size_tons': 'Chiller Size (tons)',
                'total_chillers': 'Total Units',
                'operating_chillers': 'Operating',
                'redundant_chillers': 'Redundant',
                'loading_percent': 'Loading %',
                'ten_year_tco': '10-Yr TCO ($)',
                'tco_per_mw': 'TCO/MW ($/MW)',
                'annual_energy_cost': 'Annual Energy ($)'
            }
            
            display_df = chiller_df[list(display_columns.keys())].copy()
            display_df = display_df.rename(columns=display_columns)
            
            # Format currency columns
            currency_cols = ['10-Yr TCO ($)', 'TCO/MW ($/MW)', 'Annual Energy ($)']
            for col in currency_cols:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
            
            # Format percentage column
            if 'Loading %' in display_df.columns:
                display_df['Loading %'] = display_df['Loading %'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(display_df, use_container_width=True)
            
            # Best option details
            st.subheader("Recommended Configuration")
            best = chiller_results[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Chiller Size", f"{best['chiller_size_tons']:.0f} tons")
                st.metric("Total Units", f"{best['total_chillers']}")
            with col2:
                st.metric("Operating Load", f"{best['loading_percent']:.1f}%")
                st.metric("Redundancy", f"{best['redundancy_percent']:.1f}%")
            with col3:
                st.metric("COP", f"{best['cop']:.1f}")
                st.metric("kW/ton", f"{best['kw_per_ton']:.2f}")
            with col4:
                st.metric("10-Year TCO", f"${best['ten_year_tco']:,.0f}")
                st.metric("Cost/MW", f"${best['tco_per_mw']:,.0f}/MW")
        
        else:
            st.error("No suitable chiller configurations found. Try adjusting the constraints.")
        
        # Visualization section
        st.header("📈 Design Charts")
        
        # Get main flow rate for charts
        main_flow_gpm = main_result.get('Flow Rate (GPM)', 0)
        
        tab1, tab2 = st.tabs(["Velocity vs Diameter", "Pressure Drop vs Diameter"])
        
        with tab1:
            st.subheader("Velocity vs Pipe Diameter")
            velocity_chart = create_velocity_chart(main_flow_gpm)
            st.plotly_chart(velocity_chart, use_container_width=True)
            
            # Download button
            if st.button("📥 Download Velocity Chart", key="vel_download"):
                download_chart_as_png(velocity_chart, "velocity_vs_diameter.png")
        
        with tab2:
            st.subheader("Pressure Drop vs Pipe Diameter")
            pressure_chart = create_pressure_drop_chart(target_velocity, density, viscosity)
            st.plotly_chart(pressure_chart, use_container_width=True)
            
            # Download button
            if st.button("📥 Download Pressure Drop Chart", key="pd_download"):
                download_chart_as_png(pressure_chart, "pressure_drop_vs_diameter.png")
    
    else:
        # Show welcome message when not running
        st.info("👈 Configure your system parameters in the sidebar and click 'Run Sizing Analysis' to begin.")
        
        # Show example results or documentation
        st.header("📋 About This Tool")
        st.markdown("""
        This professional data center pipe sizing tool provides:
        
        **🔧 Pipe Sizing:**
        - Calculates optimal pipe diameters for chilled water systems
        - Considers velocity limits and pressure drop constraints
        - Uses standard pipe schedules for realistic sizing
        - Supports riser calculations for multi-floor buildings
        
        **❄️ Chiller Selection:**
        - Multiple redundancy strategies (N+1, N+2, N+%)
        - Cost-optimized configurations with TCO analysis
        - Energy efficiency calculations (COP, kW/ton)
        - Modular vs Central chiller strategies
        
        **📈 Visualization:**
        - Interactive charts for design verification
        - Velocity vs diameter relationships
        - Pressure drop analysis
        - Downloadable PNG charts for documentation
        
        **🎯 Key Features:**
        - Professional-grade calculations
        - Real fluid property database
        - Industry-standard pipe schedules
        - Economic analysis with lifecycle costs
        """)

def create_velocity_chart(flow_rate_gpm):
    """Create velocity vs diameter chart using Plotly."""
    
    # Convert GPM to ft³/s
    flow_rate_cfs = flow_rate_gpm / 448.831
    
    # Range of pipe diameters (inches)
    diameters_in = np.linspace(6, 48, 100)
    diameters_ft = diameters_in / 12
    
    # Calculate velocities
    velocities = []
    for d_ft in diameters_ft:
        area_ft2 = math.pi * (d_ft / 2) ** 2
        velocity = flow_rate_cfs / area_ft2
        velocities.append(velocity)
    
    # Standard pipe sizes
    standard_sizes = [6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36, 42, 48]
    standard_velocities = []
    for size in standard_sizes:
        d_ft = size / 12
        area_ft2 = math.pi * (d_ft / 2) ** 2
        vel = flow_rate_cfs / area_ft2
        standard_velocities.append(vel)
    
    # Create plot
    fig = go.Figure()
    
    # Main curve
    fig.add_trace(go.Scatter(
        x=diameters_in,
        y=velocities,
        mode='lines',
        name='Velocity vs Diameter',
        line=dict(color='blue', width=3)
    ))
    
    # Standard sizes
    fig.add_trace(go.Scatter(
        x=standard_sizes,
        y=standard_velocities,
        mode='markers',
        name='Standard Pipe Sizes',
        marker=dict(color='red', size=10),
        text=[f'{size}"' for size in standard_sizes],
        textposition="top center"
    ))
    
    # Guidelines
    fig.add_hline(y=6, line_dash="dash", line_color="green", 
                  annotation_text="Typical Min Velocity (6 ft/s)")
    fig.add_hline(y=12, line_dash="dash", line_color="orange", 
                  annotation_text="Typical Max Velocity (12 ft/s)")
    
    fig.update_layout(
        title=f'Pipe Velocity vs Diameter<br>Flow Rate: {flow_rate_gpm:,.0f} GPM',
        xaxis_title='Pipe Diameter (inches)',
        yaxis_title='Velocity (ft/s)',
        showlegend=True,
        height=500
    )
    
    return fig

def create_pressure_drop_chart(velocity, density, viscosity):
    """Create pressure drop vs diameter chart using Plotly."""
    
    # Range of pipe diameters
    diameters_in = np.linspace(6, 48, 100)
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
    
    # Create plot
    fig = go.Figure()
    
    # Main curve
    fig.add_trace(go.Scatter(
        x=diameters_in,
        y=pressure_drops,
        mode='lines',
        name='Pressure Drop vs Diameter',
        line=dict(color='blue', width=3)
    ))
    
    # Standard sizes
    fig.add_trace(go.Scatter(
        x=standard_sizes,
        y=standard_dp,
        mode='markers',
        name='Standard Pipe Sizes',
        marker=dict(color='red', size=10),
        text=[f'{size}"<br>{dp:.1f} psi' for size, dp in zip(standard_sizes, standard_dp)],
        textposition="top center"
    ))
    
    # Guidelines
    fig.add_hline(y=5, line_dash="dash", line_color="green", 
                  annotation_text="Low ΔP (5 psi/100ft)")
    fig.add_hline(y=10, line_dash="dash", line_color="orange", 
                  annotation_text="Moderate ΔP (10 psi/100ft)")
    fig.add_hline(y=20, line_dash="dash", line_color="red", 
                  annotation_text="High ΔP (20 psi/100ft)")
    
    fig.update_layout(
        title=f'Pressure Drop vs Pipe Diameter<br>Velocity: {velocity} ft/s, Fluid: Water',
        xaxis_title='Pipe Diameter (inches)',
        yaxis_title='Pressure Drop (psi per 100 ft)',
        showlegend=True,
        height=500
    )
    
    return fig

def download_chart_as_png(fig, filename):
    """Provide download link for chart as PNG."""
    # Convert plot to image
    img_bytes = fig.to_image(format="png", width=1200, height=600)
    
    # Create download link
    b64 = base64.b64encode(img_bytes).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download {filename}</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success(f"Chart ready for download: {filename}")

if __name__ == "__main__":
    main()