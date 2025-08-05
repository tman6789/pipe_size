"""
Pressure‐drop calculations (Darcy–Weisbach).
"""

def reynolds_number(diameter, velocity, density, viscosity):
    return (density * velocity * diameter) / viscosity

def friction_factor(re):
    if re < 2000:
        return 64 / re
    # Turbulent flow (Blasius approximation)
    return 0.3164 / (re**0.25)

def darcy_pressure_drop(length, diameter, density, velocity, viscosity):
    """
    Returns ∆P (Pa) for a straight pipe of given length & diameter.
    """
    re = reynolds_number(diameter, velocity, density, viscosity)
    f = friction_factor(re)
    return f * (length / diameter) * (density * velocity**2 / 2)