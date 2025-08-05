#!/usr/bin/env python3
"""
Main script for Data Center Pipe Sizer tool.
Calculates pipe diameter based on mass flow, fluid properties, and pressure drop constraints.
"""

import math

def pipeline_sizing(mass_flow_rate, density, viscosity, pipe_length, max_pressure_drop, max_velocity):
    """
    Perform pipeline sizing based on engineering procedures.

    Parameters:
        mass_flow_rate (float): Mass flow rate (kg/s).
        density (float): Fluid density (kg/m^3).
        viscosity (float): Fluid dynamic viscosity (Pa.s).
        pipe_length (float): Length of the pipeline (m).
        max_pressure_drop (float): Maximum allowable pressure drop (Pa).
        max_velocity (float): Maximum allowable velocity (m/s).

    Returns:
        dict: Contains the calculated parameters (pipe diameter, velocity, Reynolds number, friction factor, pressure drop).
    """

    def reynolds_number(diameter, velocity):
        return (density * velocity * diameter) / viscosity

    def darcy_weisbach_friction_factor(re):
        if re < 2000:
            # Laminar flow
            return 64 / re
        else:
            # Turbulent flow (approximation using Blasius equation)
            return 0.3164 / (re ** 0.25)

    def pressure_drop(friction_factor, velocity, diameter):
        return friction_factor * (pipe_length / diameter) * (density * velocity**2 / 2)

    # Start sizing
    diameter = 0.05  # Initial guess for diameter in meters
    velocity = 0
    re = 0
    friction_factor = 0
    dp = 0

    while True:
        # Calculate velocity from the continuity equation
        area = math.pi * (diameter / 2) ** 2
        velocity = mass_flow_rate / (density * area)

        if velocity > max_velocity:
            # Increase diameter if velocity exceeds the maximum
            diameter += 0.01
            continue

        # Calculate Reynolds number
        re = reynolds_number(diameter, velocity)

        # Calculate friction factor
        friction_factor = darcy_weisbach_friction_factor(re)

        # Calculate pressure drop
        dp = pressure_drop(friction_factor, velocity, diameter)

        if dp > max_pressure_drop:
            # Increase diameter if pressure drop exceeds the maximum
            diameter += 0.01
            continue

        # Check if all conditions are satisfied
        if velocity <= max_velocity and dp <= max_pressure_drop:
            break

    return {
        "Pipe Diameter (m)": diameter,
        "Velocity (m/s)": velocity,
        "Reynolds Number": re,
        "Friction Factor": friction_factor,
        "Pressure Drop (Pa)": dp,
    }

if __name__ == "__main__":
    result = pipeline_sizing(
        mass_flow_rate=2.0,  # kg/s
        density=1000.0,      # kg/m^3
        viscosity=0.001,     # Pa.s
        pipe_length=50.0,    # m
        max_pressure_drop=50000.0,  # Pa
        max_velocity=3.0     # m/s
    )

    for key, value in result.items():
        print(f"{key}: {value}")
