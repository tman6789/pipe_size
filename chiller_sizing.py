#!/usr/bin/env python3
"""
Advanced chiller sizing script for data center applications.
Determines optimal chiller configuration with redundancy, efficiency, and cost analysis.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

class RedundancyModel(Enum):
    N_PLUS_1 = "N+1"
    N_PLUS_2 = "N+2" 
    N_PLUS_PERCENT = "N+%"

class ChillerStrategy(Enum):
    MODULAR = "Modular (Many Small Chillers)"
    CENTRAL = "Central (Few Large Chillers)"
    BALANCED = "Balanced (Medium Chillers)"

@dataclass
class ChillerSpecs:
    """Chiller specifications including efficiency and costs."""
    size_mw: float
    size_tons: float  # Cooling tons (1 MW ≈ 284 tons)
    cop: float  # Coefficient of Performance
    kw_per_ton: float  # Electrical efficiency
    install_cost_per_ton: float  # $/ton installed
    annual_maintenance_cost: float  # $/year per chiller
    
# Standard chiller catalog with realistic specs
STANDARD_CHILLERS = {
    0.35: ChillerSpecs(0.35, 100, 5.8, 0.61, 1200, 8000),    # 100 ton
    0.53: ChillerSpecs(0.53, 150, 6.2, 0.57, 1150, 10000),   # 150 ton
    0.70: ChillerSpecs(0.70, 200, 6.5, 0.54, 1100, 12000),   # 200 ton
    1.05: ChillerSpecs(1.05, 300, 6.8, 0.52, 1050, 15000),  # 300 ton
    1.40: ChillerSpecs(1.40, 400, 7.0, 0.50, 1000, 18000),  # 400 ton
    1.75: ChillerSpecs(1.75, 500, 7.2, 0.49, 980, 22000),   # 500 ton
    2.63: ChillerSpecs(2.63, 750, 7.5, 0.47, 950, 28000),   # 750 ton
    3.50: ChillerSpecs(3.50, 1000, 7.8, 0.45, 920, 35000),  # 1000 ton
    5.25: ChillerSpecs(5.25, 1500, 8.0, 0.44, 900, 45000),  # 1500 ton
    7.00: ChillerSpecs(7.00, 2000, 8.2, 0.43, 880, 55000),  # 2000 ton
}

def get_chillers_by_strategy(strategy: ChillerStrategy) -> Dict[float, ChillerSpecs]:
    """Filter available chillers based on strategy."""
    if strategy == ChillerStrategy.MODULAR:
        # Focus on smaller chillers (100-500 tons)
        return {k: v for k, v in STANDARD_CHILLERS.items() if v.size_tons <= 500}
    elif strategy == ChillerStrategy.CENTRAL:
        # Focus on larger chillers (750+ tons)
        return {k: v for k, v in STANDARD_CHILLERS.items() if v.size_tons >= 750}
    else:  # BALANCED
        # All chillers available
        return STANDARD_CHILLERS

def advanced_chiller_sizing(
    total_mw: float,
    redundancy_model: RedundancyModel = RedundancyModel.N_PLUS_1,
    redundancy_percent: float = 20.0,
    strategy: ChillerStrategy = ChillerStrategy.BALANCED,
    max_chillers: int = 20,
    min_loading_percent: float = 40.0,
    max_loading_percent: float = 80.0,
    electricity_rate: float = 0.12,  # $/kWh
    annual_hours: int = 8760
) -> List[Dict]:
    """
    Advanced chiller sizing with multiple redundancy models and efficiency analysis.
    
    Args:
        total_mw: Total building cooling load in MW
        redundancy_model: Type of redundancy (N+1, N+2, N+%)
        redundancy_percent: Percent redundancy for N+% model
        strategy: Chiller strategy (modular, central, balanced)
        max_chillers: Maximum number of chillers allowed
        min_loading_percent: Minimum chiller loading for efficiency
        max_loading_percent: Maximum chiller loading for efficiency
        electricity_rate: Electricity cost ($/kWh)
        annual_hours: Annual operating hours
    
    Returns:
        List of chiller configuration dictionaries with detailed analysis
    """
    
    # Filter chillers based on strategy
    available_chillers = get_chillers_by_strategy(strategy)
    
    results = []
    
    for chiller_mw, specs in available_chillers.items():
        # Calculate base number of chillers needed
        base_chillers = math.ceil(total_mw / (chiller_mw * (max_loading_percent / 100)))
        
        # Apply redundancy model
        if redundancy_model == RedundancyModel.N_PLUS_1:
            total_chillers = base_chillers + 1
            redundant_chillers = 1
        elif redundancy_model == RedundancyModel.N_PLUS_2:
            total_chillers = base_chillers + 2
            redundant_chillers = 2
        else:  # N_PLUS_PERCENT
            redundant_capacity = total_mw * (redundancy_percent / 100)
            redundant_chillers = math.ceil(redundant_capacity / chiller_mw)
            total_chillers = base_chillers + redundant_chillers
        
        # Check constraints
        if total_chillers > max_chillers:
            continue
            
        # Must have at least 2 chillers for any redundancy
        if total_chillers < 2:
            total_chillers = 2
            redundant_chillers = 1
            base_chillers = 1
        
        # Calculate operating characteristics
        operating_chillers = total_chillers - redundant_chillers
        total_capacity_mw = total_chillers * chiller_mw
        actual_loading_percent = (total_mw / (operating_chillers * chiller_mw)) * 100
        
        # Skip if loading is outside acceptable range
        if actual_loading_percent > max_loading_percent or actual_loading_percent < min_loading_percent:
            continue
        
        # Calculate redundancy metrics
        redundancy_capacity_mw = redundant_chillers * chiller_mw
        redundancy_percent_actual = (redundancy_capacity_mw / total_mw) * 100
        
        # Calculate energy consumption
        operating_tons = operating_chillers * specs.size_tons * (actual_loading_percent / 100)
        annual_kwh = operating_tons * specs.kw_per_ton * annual_hours
        annual_energy_cost = annual_kwh * electricity_rate
        
        # Calculate lifecycle costs
        total_tons = total_chillers * specs.size_tons
        installation_cost = total_tons * specs.install_cost_per_ton
        annual_maintenance_cost = total_chillers * specs.annual_maintenance_cost
        
        # Calculate 10-year total cost of ownership
        ten_year_tco = installation_cost + (annual_energy_cost + annual_maintenance_cost) * 10
        
        results.append({
            'chiller_size_mw': chiller_mw,
            'chiller_size_tons': specs.size_tons,
            'total_chillers': total_chillers,
            'operating_chillers': operating_chillers,
            'redundant_chillers': redundant_chillers,
            'total_capacity_mw': round(total_capacity_mw, 1),
            'total_capacity_tons': round(total_tons, 0),
            'loading_percent': round(actual_loading_percent, 1),
            'redundancy_percent': round(redundancy_percent_actual, 1),
            'cop': specs.cop,
            'kw_per_ton': specs.kw_per_ton,
            'annual_kwh': round(annual_kwh, 0),
            'annual_energy_cost': round(annual_energy_cost, 0),
            'installation_cost': round(installation_cost, 0),
            'annual_maintenance_cost': round(annual_maintenance_cost, 0),
            'ten_year_tco': round(ten_year_tco, 0),
            'tco_per_mw': round(ten_year_tco / total_mw, 0),
        })
    
    # Sort by 10-year TCO per MW (most cost-effective first)
    results.sort(key=lambda x: x['tco_per_mw'])
    
    return results

def display_advanced_chiller_options(results: List[Dict], total_mw: float):
    """Display advanced chiller configuration options with cost analysis."""
    print(f"\nAdvanced Chiller Analysis for {total_mw} MW Total Load:\n")
    
    # Summary table
    print("=== TOP CONFIGURATIONS (by Cost Effectiveness) ===")
    print("Option | Size    | Total | Operating | Redundant | Loading | 10-Yr TCO  | TCO/MW   | Annual")
    print("       | (tons)  | Units | Chillers  | Chillers  | %       | ($M)       | ($/MW)   | Energy")
    print("-" * 95)
    
    for i, result in enumerate(results[:5], 1):
        tco_millions = result['ten_year_tco'] / 1_000_000
        annual_energy_k = result['annual_energy_cost'] / 1000
        print(f"{i:6d} | {result['chiller_size_tons']:7.0f} | "
              f"{result['total_chillers']:5d} | {result['operating_chillers']:9d} | "
              f"{result['redundant_chillers']:9d} | {result['loading_percent']:7.1f} | "
              f"{tco_millions:10.1f} | {result['tco_per_mw']:8.0f} | "
              f"{annual_energy_k:7.0f}k")
    
    if results:
        print("\n=== DETAILED ANALYSIS (Best Option) ===")
        best = results[0]
        print(f"Chiller Model: {best['chiller_size_tons']:.0f} ton ({best['chiller_size_mw']:.1f} MW) units")
        print(f"Configuration: {best['total_chillers']} total ({best['operating_chillers']} operating + {best['redundant_chillers']} redundant)")
        print(f"Total Capacity: {best['total_capacity_mw']:.1f} MW ({best['total_capacity_tons']:.0f} tons)")
        print(f"Operating Load: {best['loading_percent']:.1f}% (optimal efficiency range)")
        print(f"Redundancy: {best['redundancy_percent']:.1f}% spare capacity")
        
        print(f"\nEfficiency Metrics:")
        print(f"COP: {best['cop']:.1f}")
        print(f"kW/ton: {best['kw_per_ton']:.2f}")
        print(f"Annual Energy: {best['annual_kwh']:,} kWh")
        
        print(f"\nCost Analysis:")
        print(f"Installation Cost: ${best['installation_cost']:,}")
        print(f"Annual Energy Cost: ${best['annual_energy_cost']:,}")
        print(f"Annual Maintenance: ${best['annual_maintenance_cost']:,}")
        print(f"10-Year TCO: ${best['ten_year_tco']:,}")
        print(f"Cost per MW: ${best['tco_per_mw']:,}/MW over 10 years")

def get_advanced_chiller_inputs():
    """Get comprehensive inputs for advanced chiller sizing."""
    print("\n" + "=" * 50)
    print("   ADVANCED DATA CENTER CHILLER SIZING TOOL")
    print("=" * 50)
    
    total_mw = float(input("Total Building Cooling Load (MW): "))
    
    print("\nRedundancy Model:")
    print("1. N+1 (One spare chiller)")
    print("2. N+2 (Two spare chillers)")
    print("3. N+% (Percentage-based redundancy)")
    
    redundancy_choice = input("Select redundancy model [1-3, default 1]: ").strip() or "1"
    if redundancy_choice == "2":
        redundancy_model = RedundancyModel.N_PLUS_2
        redundancy_percent = 0
    elif redundancy_choice == "3":
        redundancy_model = RedundancyModel.N_PLUS_PERCENT
        redundancy_percent = float(input("Redundancy percentage [default 20%]: ") or 20)
    else:
        redundancy_model = RedundancyModel.N_PLUS_1
        redundancy_percent = 0
    
    print("\nChiller Strategy:")
    print("1. Modular (Many small chillers, high redundancy)")
    print("2. Central (Few large chillers, low footprint)")
    print("3. Balanced (Medium-sized chillers)")
    
    strategy_choice = input("Select strategy [1-3, default 3]: ").strip() or "3"
    if strategy_choice == "1":
        strategy = ChillerStrategy.MODULAR
    elif strategy_choice == "2":
        strategy = ChillerStrategy.CENTRAL
    else:
        strategy = ChillerStrategy.BALANCED
    
    max_chillers = int(input("Maximum number of chillers allowed [default 20]: ") or 20)
    electricity_rate = float(input("Electricity rate ($/kWh) [default 0.12]: ") or 0.12)
    
    return {
        'total_mw': total_mw,
        'redundancy_model': redundancy_model,
        'redundancy_percent': redundancy_percent,
        'strategy': strategy,
        'max_chillers': max_chillers,
        'electricity_rate': electricity_rate
    }

# Legacy function for backward compatibility
def chiller_sizing(total_mw):
    """Simple chiller sizing for backward compatibility."""
    results = advanced_chiller_sizing(total_mw)
    # Convert to old format for compatibility
    legacy_results = []
    for r in results:
        legacy_results.append({
            'chiller_size_mw': r['chiller_size_mw'],
            'total_chillers': r['total_chillers'],
            'operating_chillers': r['operating_chillers'],
            'spare_chillers': r['redundant_chillers'],
            'total_capacity_mw': r['total_capacity_mw'],
            'loading_percent': r['loading_percent'],
            'redundancy_percent': r['redundancy_percent'],
        })
    return legacy_results

if __name__ == "__main__":
    inputs = get_advanced_chiller_inputs()
    
    results = advanced_chiller_sizing(
        total_mw=inputs['total_mw'],
        redundancy_model=inputs['redundancy_model'],
        redundancy_percent=inputs['redundancy_percent'],
        strategy=inputs['strategy'],
        max_chillers=inputs['max_chillers'],
        electricity_rate=inputs['electricity_rate']
    )
    
    if results:
        display_advanced_chiller_options(results, inputs['total_mw'])
    else:
        print("No suitable chiller configurations found for the specified parameters.")
        print("Try adjusting constraints or redundancy requirements.")