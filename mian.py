#!/usr/bin/env python3
"""
Main script for Data Center Pipe Sizer tool.
"""

import math
from calc.inputs import get_inputs

def pipeline_sizing(mass_flow_rate, density, viscosity, pipe_length, max_pressure_drop, max_velocity):
    """
    Perform pipeline sizing based on Imperial units.
    Inputs:
        mass_flow_rate: lb/hr
        density: lb/ft³
        viscosity: lb/ft·s
        pipe_length: ft
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

    return {
        "Pipe Diameter (in)": diameter * 12,
        "Velocity (ft/s)": velocity,
        "Reynolds Number": re,
        "Friction Factor": f,
        "Pressure Drop (psi)": dp / 144,
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
        pipe_length=inputs["length"],
        max_pressure_drop=inputs["max_dp"] * 144,  # psi to lb/ft²
        max_velocity=inputs["velocity"]
    )
    for key, value in result.items():
        print(f"{key}: {value}")
