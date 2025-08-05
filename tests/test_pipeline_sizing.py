#!/usr/bin/env python3
"""
Main script for Data Center Pipe Sizer tool.
"""

import math
import argparse

def pipeline_sizing(mass_flow_rate, density, viscosity, pipe_length, max_pressure_drop, max_velocity):
    """
    Perform pipeline sizing based on engineering procedures.
    """
    def reynolds_number(diameter, velocity):
        return (density * velocity * diameter) / viscosity

    def friction_factor(re):
        if re < 2000:
            return 64 / re
        return 0.3164 / (re ** 0.25)

    def pressure_drop(f, velocity, diameter):
        return f * (pipe_length / diameter) * (density * velocity**2 / 2)

    diameter = 0.05  # initial guess (m)
    while True:
        area = math.pi * (diameter / 2) ** 2
        velocity = mass_flow_rate / (density * area)
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
        "Pipe Diameter (m)": diameter,
        "Velocity (m/s)": velocity,
        "Reynolds Number": re,
        "Friction Factor": f,
        "Pressure Drop (Pa)": dp,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Center Pipe Sizer CLI")
    parser.add_argument("--mw", type=float, required=True, help="Cooling load in MW")
    parser.add_argument("--dt", "--delta_t", type=float, dest="delta_t", required=True,
                        help="Temperature difference ΔT in °F")
    parser.add_argument("--velocity", type=float, default=6.0,
                        help="Target fluid velocity in ft/s (default: 6)")
    parser.add_argument("--density", type=float, default=1000.0,
                        help="Fluid density in kg/m³ (default: 1000)")
    parser.add_argument("--viscosity", type=float, default=0.001,
                        help="Fluid dynamic viscosity in Pa.s (default: 0.001)")
    parser.add_argument("--length", type=float, default=50.0,
                        help="Pipe length in m for pressure drop calculation (default: 50)")
    parser.add_argument("--max_dp", "--max_pressure_drop", type=float, dest="max_dp",
                        default=50000.0, help="Max allowable pressure drop in Pa (default: 50000)")
    args = parser.parse_args()

    # Convert MW to mass flow rate (kg/s) using Cp = 4186 J/kg·K
    mass_flow_rate = args.mw * 1e6 / (4186 * args.delta_t)
    result = pipeline_sizing(
        mass_flow_rate=mass_flow_rate,
        density=args.density,
        viscosity=args.viscosity,
        pipe_length=args.length,
        max_pressure_drop=args.max_dp,
        max_velocity=args.velocity
    )
    for key, value in result.items():
        print(f"{key}: {value}")