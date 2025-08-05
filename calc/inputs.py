def get_inputs():
    print("Enter Data Center Pipe Sizer inputs (Imperial units):")
    mw = float(input("Cooling Load (MW): "))
    delta_t = float(input("ΔT (°F): "))
    velocity = float(input("Target Velocity (ft/s) [default 6]: ") or 6)
    density = float(input("Fluid Density (lb/ft³) [default 62.4]: ") or 62.4)
    viscosity = float(input("Dynamic Viscosity (lb/ft·s) [default 2.73e-5]: ") or 2.73e-5)
    length = float(input("Pipe Length (ft) [default 150]: ") or 150)
    max_dp = float(input("Max Pressure Drop (psi) [default 20]: ") or 20)

    return {
        "mw": mw,
        "delta_t": delta_t,
        "velocity": velocity,
        "density": density,
        "viscosity": viscosity,
        "length": length,
        "max_dp": max_dp,
    }
