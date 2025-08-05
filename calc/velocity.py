import math

def flow_to_diameter(flow_gpm, velocity_fps):
    flow_cfs = flow_gpm / 448.831
    area = flow_cfs / velocity_fps
    diameter = math.sqrt((4 * area) / math.pi)
    return diameter  # in ft