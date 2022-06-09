"""_summary_

Returns:
    _type_: _description_
"""
import copy
from math import isnan
import pandas as pd

def get_vessel_type(pos):
    """_summary_

    Args:
        pos (_type_): _description_

    Returns:
        _type_: _description_
    """

    n=-1
    for i in pos.TYPE.unique():
        if(not isnan(i)):
            n = i
            break
    if(n>69 and n<80):
        return 'Cargo'
    if(n>79 and n<90):
        return 'Tanker'
    if(n==33):
        return 'Dredging'
    if(n>39 and n<50):
        return 'HSC'
    if(n==30):
        return 'Fishing'
    if(n==35 or n==55):
        return 'Military_Law'
    if(n>59 and n<70):
        return 'Passenger'
    if(n==37):
        return 'Pleasure'
    if(n==36):
        return 'Sailing'
    if(n in [50, 51, 53, 54, 58]):
        return 'Service'
    
    if(n in [31, 32, 52]):
        return 'Tug'
    if(n==-1):
        return 'Unknown'
    return 'Other'


# All
# Cargo
# Dredging or Underwater ops
# High Speed Craft
# Fishing
# Military and Law Enforcement
# Passenger
# Pleasure Craft
# Sailing
# Service
# Tanker
# Tug and Towing
# Other
# Unknown

grid = None
gridEL = None

def vessels_count_init(_config, _grid, _gridEL):
    """_summary_

    Args:
        _config (_type_): _description_
        _grid (_type_): _description_
        _gridEL (_type_): _description_
    """
    global grid
    global gridEL
    grid  = copy.deepcopy(_grid[['gridID']].set_index('gridID'))
    gridEL = _gridEL


def vessels_count(file_path):
    """_summary_

    Args:
        file_path (_type_): _description_

    Returns:
        _type_: _description_
    """
    pos = pd.read_csv(file_path)
    pos['xGrid'] = pos['X'] / gridEL
    pos['yGrid'] = pos['Y'] / gridEL
    pos['xGrid'] = pos['xGrid'].astype(int).astype(str)
    pos['yGrid'] = pos['yGrid'].astype(int).astype(str)
    pos['gridID'] = pos['xGrid'] + '_' + pos['yGrid']
    cellsVisited = pos['gridID'].unique()
    res= grid.loc[grid.index.intersection(cellsVisited)]
    res = res.assign(density=1)
    return res, get_vessel_type(pos)

