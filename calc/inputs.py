from .fluid_properties import get_fluid_options, get_fluid_properties, get_fluid_name

def get_inputs():
    print("Enter Data Center Pipe Sizer inputs (Imperial units):")
    mw = float(input("Total Building Cooling Load (MW): "))
    delta_t = float(input("ΔT (°F): "))
    velocity = float(input("Target Velocity (ft/s) [default 12]: ") or 12)
    
    # Fluid selection
    print("\nAvailable fluids:")
    fluid_options = get_fluid_options()
    for i, fluid_type in enumerate(fluid_options, 1):
        fluid_name = get_fluid_name(fluid_type)
        print(f"{i}. {fluid_name}")
    
    while True:
        try:
            choice = input("Select fluid type [default 1]: ") or "1"
            fluid_idx = int(choice) - 1
            if 0 <= fluid_idx < len(fluid_options):
                selected_fluid = fluid_options[fluid_idx]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    density, viscosity = get_fluid_properties(selected_fluid)
    print(f"Using {get_fluid_name(selected_fluid)} - Density: {density} lb/ft³, Viscosity: {viscosity} lb/ft·s")
    
    max_dp = float(input("Max Pressure Drop (psi) [default 20]: ") or 20)
    
    # Optional riser configuration
    num_risers_input = input("Number of risers [optional, press Enter to skip]: ").strip()
    num_risers = int(num_risers_input) if num_risers_input else None

    return {
        "mw": mw,
        "delta_t": delta_t,
        "velocity": velocity,
        "density": density,
        "viscosity": viscosity,
        "max_dp": max_dp,
        "fluid_type": selected_fluid,
        "num_risers": num_risers,
    }
