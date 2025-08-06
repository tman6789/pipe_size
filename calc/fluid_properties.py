"""
Fluid properties lookup for common HVAC fluids.
"""

# Fluid properties at standard conditions (60°F)
FLUID_PROPERTIES = {
    'water': {
        'name': 'Water',
        'density': 62.4,  # lb/ft³
        'viscosity': 2.73e-5,  # lb/ft·s
    },
    'glycol_30': {
        'name': '30% Ethylene Glycol',
        'density': 63.8,  # lb/ft³
        'viscosity': 4.2e-5,  # lb/ft·s
    },
    'glycol_50': {
        'name': '50% Ethylene Glycol',
        'density': 65.4,  # lb/ft³
        'viscosity': 8.9e-5,  # lb/ft·s
    },
}

def get_fluid_options():
    """Return list of available fluid types."""
    return list(FLUID_PROPERTIES.keys())

def get_fluid_properties(fluid_type):
    """Return density and viscosity for the specified fluid type."""
    if fluid_type not in FLUID_PROPERTIES:
        raise ValueError(f"Unknown fluid type: {fluid_type}")
    
    props = FLUID_PROPERTIES[fluid_type]
    return props['density'], props['viscosity']

def get_fluid_name(fluid_type):
    """Return the display name for a fluid type."""
    return FLUID_PROPERTIES.get(fluid_type, {}).get('name', fluid_type)