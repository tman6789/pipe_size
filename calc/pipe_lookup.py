"""
Lookup module for nominal pipe sizes.
Rounds an internal diameter (m) up to the nearest standard nominal size.
"""

import bisect

# Map nominal size → internal diameter (m). Extend as needed.
PIPE_SCHEDULE = {
    '6"': 0.1545,
    '8"': 0.2032,
    '10"': 0.2540,
    '12"': 0.3048,
    # …add more
}

def get_nominal_pipe_size(diameter_m):
    """
    Return the smallest nominal size string whose ID >= diameter_m.
    """
    sizes = sorted(PIPE_SCHEDULE.items(), key=lambda x: x[1])
    diameters = [d for _, d in sizes]
    idx = bisect.bisect_left(diameters, diameter_m)
    return sizes[min(idx, len(sizes)-1)][0]