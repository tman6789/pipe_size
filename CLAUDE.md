# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for sizing chilled-water and condenser loops in data centers based on cooling load (MW), temperature difference (ΔT), and velocity/pressure-drop constraints. The tool performs hydraulic calculations to determine appropriate pipe diameters.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies:
- numpy
- pandas

## Running the Application

The main application is in `mian.py` (note the typo in filename). Two versions exist:

### Interactive Version
```bash
python3 mian.py
```
Prompts for user inputs including cooling load, ΔT, velocity, density, viscosity, pipe length, and max pressure drop.

### CLI Version (in tests file)
```bash
python3 tests/test_pipeline_sizing.py --mw 5.0 --dt 10.0 --velocity 6.0
```
Command-line interface with arguments for all parameters.

## Testing

Uses Python's built-in unittest module:
```bash
python3 -m unittest discover tests/
python3 -m unittest tests/test_pipeline_sizing.py
```

## Code Architecture

### Main Module (`mian.py`)
- Contains the core `pipeline_sizing()` function
- Performs iterative diameter calculation based on velocity and pressure drop constraints
- Uses Imperial units (lb/hr, lb/ft³, ft/s, psi)

### Calculation Modules (`calc/`)
- `inputs.py`: Interactive input gathering
- `flow.py`: MW to GPM conversion utility
- `velocity.py`: Flow rate to diameter conversion
- `pressure_drop.py`: Darcy-Weisbach pressure drop calculations
- `pipe_lookup.py`: Standard pipe size lookup functionality

### Data
- `data/Standard_Pipe_Schedule.csv`: Standard pipe dimensions

## Unit Consistency

The codebase has mixed unit systems:
- Main script (`mian.py`): Imperial units
- Test/CLI version: Metric units  
- Individual calc modules: Various units

When modifying calculations, pay careful attention to unit conversions and ensure consistency within each module.