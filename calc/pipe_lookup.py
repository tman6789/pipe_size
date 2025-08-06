"""
Lookup module for nominal pipe sizes.
Rounds an internal diameter (m) up to the nearest standard nominal size.
"""

import bisect

# Map nominal size → internal diameter (inches). Standard Schedule 40 pipe.
PIPE_SCHEDULE = {
    '6"': 6.065,
    '8"': 7.981,
    '10"': 10.020,
    '12"': 11.938,
    '14"': 13.124,
    '16"': 15.000,
    '18"': 16.876,
    '20"': 18.812,
    '24"': 22.624,
    '30"': 28.750,
    '36"': 34.500,
    '42"': 40.250,
    '48"': 46.000,
}

def get_nominal_pipe_size(diameter_inches):
    """
    Return the smallest nominal size string whose ID >= diameter_inches.
    """
    sizes = sorted(PIPE_SCHEDULE.items(), key=lambda x: x[1])
    diameters = [d for _, d in sizes]
    idx = bisect.bisect_left(diameters, diameter_inches)
    if idx >= len(sizes):
        return sizes[-1][0]  # Return largest size if diameter is too big
    return sizes[idx][0]

def get_pipe_id(nominal_size):
    """
    Return the internal diameter in inches for a given nominal size.
    """
    return PIPE_SCHEDULE.get(nominal_size, None)