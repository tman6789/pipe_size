def mw_to_gpm(mw, delta_t_f):
    """
    Convert MW cooling load to GPM flow rate for chilled water.
    
    Formula: GPM = (MW × 3,412,000 BTU/hr/MW) / (500 BTU/°F/GPM × ΔT°F)
    
    Args:
        mw: Cooling load in megawatts
        delta_t_f: Temperature difference in °F
    
    Returns:
        Flow rate in GPM
    """
    return (mw * 3412000) / (500 * delta_t_f)