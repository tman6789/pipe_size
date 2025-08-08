# Data Center Pipe Sizer

A Python tool to size chilled‐water and condenser loops in data centers based on
cooling load (MW), ΔT, and velocity/pressure‐drop constraints.

## V2 Features & Deploy

### What's New in V2

**🏢 Layout-Based Sizing**
- Configure data center layout using `C×R×F` format (Columns × Rows × Floors)
- Per-hall MW load inputs with editable DataFrame interface
- Visual layout heatmap with riser placement options

**⚙️ Enhanced Riser Analysis**  
- Shared riser sizing by column aggregation
- Individual hall sizing option
- Interactive riser stack bar charts

**📊 Interactive Plotly Charts**
- Velocity vs diameter curves
- Pressure drop analysis charts  
- Layout heatmaps with load visualization
- Professional `plotly_white` theme

**🔧 Engineering Improvements**
- ΔP normalized to psi per 100 ft everywhere
- Velocity warnings for segments >10 ft/s
- Enhanced chiller sizing with tons (alongside MW)
- Fan heat percentage factor for cooling loads

**☁️ Cloud Deployment Ready**
- Render.com compatible with proper port binding
- All dependencies in requirements.txt
- Environment variable support for PORT

### Live Demo

Deploy to Render.com or run locally:

```bash
# Local development
python3 gradio_app.py

# With public sharing
python3 gradio_app.py --share

# Cloud deployment (uses PORT environment variable)
python3 gradio_app.py
```

### CLI Calculator (Enhanced V2)

Run the enhanced command-line calculator:

```bash
python main.py
```

**Features:**
- **Quick Sizing**: Simple MW + ΔT input for basic pipe sizing
- **Layout Analysis**: Advanced C×R×F layout with per-hall loads
- **Smart Input Validation**: Guided prompts with error checking
- **Velocity Warnings**: Automatic alerts for >10 ft/s velocities
- **Integrated Flow**: Pipe sizing → Riser analysis → Chiller recommendations

**Example CLI Workflow:**
1. **Select Mode**: Quick sizing (1) or Layout analysis (2)
2. **Layout Input**: `4×3×2` (4 columns, 3 rows, 2 floors = 24 halls)
3. **Load Distribution**: Same MW for all halls or individual inputs
4. **Parameters**: ΔT, velocity, fluid type, max ΔP
5. **Results**: Main pipe + riser analysis + chiller recommendations

### Web Interface Usage

1. **Layout**: Enter `4×3×2` for 4 columns, 3 rows, 2 floors (24 total halls)
2. **Load Distribution**: Choose "Use same MW for all halls" or edit per-hall loads
3. **Riser Strategy**: Enable "Shared risers among halls" for column aggregation
4. **Analysis**: Get interactive charts and comprehensive sizing tables

### Architecture

- `calc/layout.py` - Layout parsing and hall name generation
- `calc/visualization.py` - Plotly chart generation  
- `gradio_app.py` - V2 web interface with enhanced features
- `main.py` - Core pipeline sizing algorithms (Imperial units)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt