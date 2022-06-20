"""TODO summary

Returns:
    _type_: _description_
"""
import sys
import logging
import time
import os
import copy
import json


from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from mt.density.time_at_cells import time_at_cells,time_at_cells_init
from mt.utils.get_grid import load_grids
from mt.density.density_utils import vessels_count,vessels_count_init
from mt.utils.outputFileUtils import check_if_path_exists
# from mt.density.lineCrossings import line_crossings



def get_density(config, gridEdgeLength=-1, ais_files_path=''):
    """
            This function loads configuration extracts csv file with respect to 
            the selected density method ('time_at_cells' or 'vessels_count')
    """
    

    if(ais_files_path==''):
        ais_files_path=config['ais_cleaned_path']
    if(gridEdgeLength!=-1):
        gridEL = gridEdgeLength
    else:
        gridEL = config['grid_edge_lengths'][-1]
    grid = load_grids(config)[gridEL]


    _resTypes = config.get('density_vessel_types', ['All'])
    allVTypes = ['All', 'Cargo', 'Tanker', 'Dredging', 'HSC', 'Fishing', 'Military_Law', 'Passenger', 'Pleasure', 'Sailing', 'Service', 'Tug', 'Unknown', 'Other']
    if(_resTypes==['Everything']):
        resTypes=allVTypes
    else:
        resTypes = []
        for type in _resTypes:
            if(type in allVTypes):
                resTypes.append(type)

    maxThreads = config.get('max_threads', 4)
    if(config['density_method']=='time_at_cells'):
        dmethod = time_at_cells
        dmethod_init = time_at_cells_init
    else:
        dmethod = vessels_count
        dmethod_init = vessels_count_init
        config['density_method'] = "vessels_count"

    _outpath = config['density_path']+'density'+'_'+config['density_method']+'_'+str(gridEL)


    for vType in resTypes:
        tempPath = _outpath+'_'+vType+'.csv'
        if(not check_if_path_exists(tempPath)):
            break
    else:
        logging.warning('\tDensity files found at %s',config['density_path'])
        return  resTypes, _outpath


    try:
        fsizes = pd.read_csv(config['ais_stats_path']+'cleaning_stats.csv')
        fsizes = dict(zip(fsizes['mmsi'], fsizes['output_rows']))
    except Exception:
        fsizes = {}
    minPos = config.get('min_positions_density', 5)


    t_0 = time.time()
    _results = grid[['gridID']]
    _results = _results.assign(density=0)
    _results.set_index('gridID', inplace=True)
    _results.rename_axis(None, axis=0, inplace=True)

    results = {}
    for type in resTypes:
        results[type] = copy.deepcopy(_results)
    del _results

    logging.warning('\tEstimating density, using the metric: \"%s\" ...', dmethod.__name__)
    futures = {}
    with ProcessPoolExecutor(max_workers=maxThreads, initializer=dmethod_init, initargs=(config, grid, gridEL)) as executor:
        for f in os.listdir(ais_files_path):
            if f.endswith(".csv"):
                try:
                    file_mmsi = int(f.split('/')[-1].split('_')[-2])
                except Exception:
                    file_mmsi = ''
                if(fsizes.get(file_mmsi, minPos+1)>=minPos):
                    logging.warning("Density calculation submitting file %s ", file_mmsi)
                    futures[executor.submit(dmethod, (ais_files_path+f))] = file_mmsi
        count=0
        for future in as_completed(futures):
            # try:
                res, resType = future.result()
                # t_1 = time.time()
                if('All' in resTypes):
                    results['All'] = results['All'].add(res, fill_value=0)
                if(resType in resTypes):
                    results[resType] = results[resType].add(res, fill_value=0)
                count+=1
                if(count%5==0):
                    logging.debug(f"\t{count}:  {futures[future]}")
                    logging.debug(f'About {len(executor._pending_work_items)} tasks remain')
            # except Exception as exc:
            #   logging.warning('Process exception (%s): %s'%(futures[future], exc))
    


    logging.warning('\tCalculated density.')
    logging.warning('\t\tCalculating density time: %s ', time.time()-t_0)
    grid['centroid'] = grid.geometry.centroid
    grid['lon_centroid'] = grid['centroid'].x
    grid['lat_centroid'] = grid['centroid'].y
    grid.drop(columns=['geometry', 'centroid', 'x', 'y'], inplace=True)
    for vType in resTypes:
        outpath = _outpath+'_'+vType+'.csv'
        results[vType]['gridID'] = results[vType].index
        results[vType] = results[vType].merge(grid, on='gridID')
        results[vType].to_csv(outpath, index=False)
    logging.warning('\tSaved density results at: %s',_outpath)
    return resTypes, _outpath









if __name__ == "__main__":


    
    
    config_file = open(sys.argv[1], "r",encoding='utf-8')
    config = json.load(config_file)


    

    # logging.warning("Calculating density for " + config["ais_file_path"])
    t_0 = time.time()
    get_density(config)
    logging.debug(time.time() - t_0)