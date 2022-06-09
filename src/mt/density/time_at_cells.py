
from math import isnan,dist
import copy
import pandas as pd
import geopandas as gpd
from haversine import haversine
from shapely.geometry import Point, LineString
from mt.density.density_utils import get_vessel_type

grid = None
gridEL = None
outCRS = None

def time_at_cells_init(_config, _grid, _gridEL):
    global outCRS
    global grid
    global gridEL
    outCRS = _config.get('out_crs', 3035)
    grid = copy.deepcopy(_grid[['gridID', 'geometry']])
    gridEL = _gridEL


def havdist(row):
    """
        help function to calculate the haversine distance
    """
    if isnan(row.lag_lon):
        return 0
    return haversine((row.LAT, row.LON), (row.lag_lat, row.lag_lon), unit='km')




def eucl(row):
    """
        help function to calculate the euclidean distance
    """
    if isnan(row.lag_lon):
        return 0
    return dist((row.X, row.Y), (row.lag_X, row.lag_Y))


def time_at_cells(file_path):
    """help function to calculate time 

    Args:
        file_path (str): path of the cleaned ais dataset for a vessel as produced from cleaning process

    Returns:
        tuple(pd.DataFrame,string):
            - first element is the density value including indexing 
            - the type of vessel 
    """

    pos = pd.read_csv(file_path)
    if(len(pos)==0):
        return pd.DataFrame([]), (0, 0)
    pos['xGrid'] = pos['X'] / gridEL
    pos['yGrid'] = pos['Y'] / gridEL
    pos['xGrid'] = pos['xGrid'].astype(int).astype(str)
    pos['yGrid'] = pos['yGrid'].astype(int).astype(str)
    pos['gridID'] = pos['xGrid'] + '_' + pos['yGrid']

    geometryPoints = [Point(x, y) for (x,y) in zip(pos.X, pos.Y)]
    pos = gpd.GeoDataFrame(pos, geometry=geometryPoints)
    pos.set_crs(epsg=outCRS, inplace=True)


    pos[['lag_gridID', 'lag_t', 'lag_lon', 'lag_lat', 'lag_X', 'lag_Y']] = pos[['gridID', 'TIMESTAMP', 'LON', 'LAT', 'X', 'Y']].shift(1)
    # Adding extra columns to pos data
    pos['dt'] = pos['TIMESTAMP'] - pos['lag_t']
    # Selecting transitions to be considered
    pos['ddist'] = pos.apply(lambda row: eucl(row), axis=1) #meters
    pos['calc_speed'] = pos.apply(lambda row: row['ddist']/row['dt'] if (row['dt']>0.0) else 1000.0,axis=1) #meters/milliseconds
    pos=pos[(pos.ddist<=30000) & (pos.dt<=(6*60*60*1000)) & (pos.calc_speed<=0.0257222) ]

    posGridChange = copy.deepcopy(pos[pos.gridID != pos.lag_gridID])
    posGridChange['pos_id'] = posGridChange.index
    posGridChange = posGridChange.dropna(subset=['X', 'Y', 'lag_X', 'lag_Y'], axis = 0)

    # Generate Linestrings and place them in a Geodataframe
    geometryLineStrings = [LineString([(x, y), (z,w)]) for (x,y,z,w) in zip(posGridChange.X, posGridChange.Y, posGridChange.lag_X, posGridChange.lag_Y)]
    posGridChange.geometry = gpd.GeoSeries(geometryLineStrings, index=posGridChange.index)
    posGridChange['lineLength'] = posGridChange.geometry.length
    

    # Compute overlays between grids and pos linestrings
    if(len(posGridChange)!=0):
        overlays = gpd.overlay(gpd.GeoDataFrame(posGridChange[['pos_id','geometry','lineLength','dt']]).set_crs(epsg=outCRS), grid, how='intersection')
        overlays['overlayLength'] = overlays.geometry.length
        overlays['overlayPercentage'] = overlays['overlayLength'] / overlays['lineLength']
        overlays['overlayDt'] = overlays['overlayPercentage'] * overlays['dt']
        timesAtGridChange = overlays.groupby(['gridID'])['overlayDt'].sum().rename('dtGridChange').to_frame().reset_index()

    posGridNoChange = pos[pos.gridID == pos.lag_gridID]
    posGridNoChange = posGridNoChange.dropna(subset=['X', 'Y', 'lag_X', 'lag_Y'], axis = 0)
    timesAtGridNoChange = posGridNoChange.groupby(['gridID'])['dt'].sum().rename('dtGridNoChange').to_frame().reset_index()
    

    # Computing times at cells
    if(len(posGridChange)!=0):
        timesAtCells = pd.merge(timesAtGridNoChange, timesAtGridChange, how = 'outer', left_on = ['gridID'], right_on = ['gridID'])
    else:
        timesAtCells = timesAtGridNoChange
        timesAtCells['dtGridChange'] = 0
    timesAtCells['density'] = timesAtCells[['dtGridNoChange','dtGridChange']].sum(axis=1) / (3600*1000)
    timesAtCells.set_index('gridID', inplace=True)
    timesAtCells.rename_axis(None, axis=0, inplace=True)
    return timesAtCells[['density']], get_vessel_type(pos)