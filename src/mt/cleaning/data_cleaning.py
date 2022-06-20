"""Data Cleaning module.
Returns:
    _type_: _description_
"""

import os
import sys
import csv
import time
import copy
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import pyproj
import pandas as pd
from haversine import haversine
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree
from shapely.validation import make_valid

from  mt.utils.get_grid import load_geom
from  mt.utils.auxiliary import polygon_split


CONFIG = None
SEAS_RTREE = None
PROJECT = None


def clean_init(_config, _seas_rtree, _project):
    """_summary_

    Args:
        _config (_type_): _description_
        _seas_rtree (_type_): _description_
        _project (_type_): _description_
    """
    global CONFIG
    global SEAS_RTREE
    global PROJECT
    CONFIG = copy.deepcopy(_config)
    PROJECT = _project
    if CONFIG["land_mask"]:
        SEAS_RTREE = copy.deepcopy(_seas_rtree)


def clean_mmsi(mmsi):
    """
    clean_mmsi: Given a mmsi number it performs cleaning process as described in clean_data function 
                and creates the cleaned  data file in the CONFIG["ais_cleaned_path"] folder for the provided mmsi.
                  
    Args:
        mmsi (str): The mmsi number provided in string format to retrieve the AIS merged positions 
                    dataset for a specific vessel with respect to paths defined in CONFIG["ais_path"]
                    in the configuration file.
                        

    Returns:
        (list of integers): Statistics of data removed through cleaning process in the following order
                            '[rows, rows_out, r_ef, r_imf, r_iid, r_geo, r_ds, r_spd, r_tf]'
                            
                            where :
                                rows : total input rows
                                rows_out: total rows in output
                                r_ef : removed due to empty fields
                                r_imf : removed due to invalid movement fields
                                r_iid : removed due to invalid mmsi
                                r_geo : removed due to land mask
                                r_ds : removed due to downsampling
                                r_spd : removed due to noise filtering
                                r_tf : removed due to imposed timeframe
    """
    # HEADER: TIMESTAMP,MMSI,LON,LAT,HEADING,COURSE,SPEED,NAVIGATIONAL_STATUS,TYPE,STATION,CLASS
    TS, MMSI, LON, LAT, HEAD, COG, SOG, NAVS, TYPE, STATION, CLASS = (0,1,2,3,4,5,6,7,8,9,10)
    
    del HEAD,NAVS,TYPE,STATION,CLASS # removing unused variables
    
    # COUNTERS
    rows = 0  # total input rows
    rows_out = 0  # total rows in output
    r_ef = 0  # removed due to empty fields
    r_imf = 0  # removed due to invalid movement fields
    r_iid = 0  # removed due to invalid mmsi
    r_geo = 0  # removed due to land mask
    r_ds = 0  # removed due to downsampling
    r_spd = 0  # removed due to noise filtering
    r_tf = 0  # removed due to imposed timeframe
    false_mmsi = CONFIG.get("false_mmsi", [])
    downsample_rate = CONFIG.get("downsample_rate", 0)
    max_sp = CONFIG.get("max_calc_speed", 92.0)
    
    
    if CONFIG["timeframe"]:
        tleft = CONFIG["start_time"]
        tright = CONFIG["end_time"]
        
    cleaned_output_path = os.path.join(CONFIG["ais_cleaned_path"], str(mmsi) + "_clean.csv")
    with open(cleaned_output_path, "w",encoding="utf-8") as out_file:
        out_file.write(
            "TIMESTAMP,MMSI,LON,LAT,X,Y,HEADING,COURSE,SPEED,NAVIGATIONAL_STATUS,TYPE,STATION,CLASS\n"
        )

        pt = 0
        ts = 0
        fst_flag = False
        with open(os.path.join(CONFIG["ais_path"] ,mmsi + ".csv"), "r",encoding="utf-8") as in_file:

            # print('\tReading input file (%s).'%(mmsi+'.csv'))
            next(in_file)
            for line in in_file:

                row = next(csv.reader([line]))
                rows += 1

                if CONFIG["empty_fields"]:
                    # Check on empty fields: COG, SOG, LON, LAT, TIMESTAMP.
                    if (
                        row[SOG] == ""
                        or row[COG] == ""
                        or row[LON] == ""
                        or row[LAT] == ""
                        or row[TS] == ""
                    ):
                        r_ef += 1
                        continue

                if CONFIG["invalid_movement_fields"]:
                    # Check on SOG and COG validity.
                    if (
                        float(row[SOG]) < 0.0
                        or float(row[SOG]) > 80.0
                        or float(row[COG]) < 0.0
                        or float(row[COG]) >= 360.0
                    ):
                        r_imf += 1
                        continue

                if CONFIG["invalid_mmsi"]:
                    # Check on MMSI validity.
                    if (row[MMSI] in false_mmsi) or (len(row[MMSI]) != 9):
                        r_iid += 1
                        continue


                # if config['remove_special_characters']:
                #     # Remove special characters from name and call sing.
                #     row[NAME] = re.sub('[^A-Za-z0-9 ]+', '', row[NAME])
                #     row[CALLS] = re.sub('[^A-Za-z0-9 ]+', '', row[CALLS])
                
                ts = int(row[TS])

                if CONFIG["timeframe"]:
                    if (ts < tleft) or (ts > tright):
                        r_tf += 1
                        continue

                if CONFIG["downsample"]:
                    if ts - pt <= downsample_rate:
                        r_ds += 1
                        continue

                clon = float(row[LON])
                clat = float(row[LAT])
                if CONFIG["noise_filter"]:
                    if fst_flag:
                        ddist = haversine((clat, clon), (plat, plon), unit="km")
                        cspeed = (ddist * 60.0 * 60.0 * 1000.0) / (ts - pt)
                        if cspeed > max_sp:
                            r_spd += 1
                            continue

                projected = transform(PROJECT, Point(clon, clat))
                # grid_edge_length: default->10, if different get by user
                if CONFIG["land_mask"]:
                    if (
                        len(
                            [
                                o
                                for o in SEAS_RTREE.query(projected)
                                if o.contains(projected)
                            ]
                        )
                        == 0
                    ):
                        r_geo += 1
                        continue

                plon = clon
                plat = clat
                pt = ts
                rows_out += 1
                fst_flag = True
                out_file.write(
                    f"{row[0]},{row[1]},{row[2]},{row[3]},{projected.x},{projected.y},{row[4]},{row[5]},{row[6]},{row[7]},{row[8]},{row[9]},{row[10]}\n"
                )

    if(rows_out==0):
        os.remove(cleaned_output_path)
        
    return [rows, rows_out, r_ef, r_imf, r_iid, r_geo, r_ds, r_spd, r_tf]


def clean_data(_config, _seas_tree=[], grid_edge_length=-1):
    """_summary_

    Args:
        _config (_type_): _description_
        _seas_tree (list, optional): _description_. Defaults to [].
        grid_edge_length (int, optional): _description_. Defaults to -1.

    Returns:
        _type_: _description_
    """
    ais_file = _config["ais_path"]

    # Default data parameters initialization
    out_crs = _config.get("out_crs", 3035)
    minPos = _config.get("min_positions", 10)
    maxThreads = _config.get("max_threads", 4)
    
    
    if grid_edge_length == -1:
        grid_edge_length = _config.get(
            "polygon_split_threshold", _config["grid_edge_lengths"][-1]
        )
    try:
        cin = open(_config["ais_stats_path"] + "merging_stats.json", "r",encoding='utf-8')
        fsizes = json.load(cin)
    except Exception:
        fsizes = {}
    seas_list = []

    _project = pyproj.Transformer.from_crs(
        pyproj.CRS("EPSG:4326"), pyproj.CRS("EPSG:" + str(out_crs)), always_xy=True
    ).transform

    if ("geometry_file_path" not in _config) and ("bounding_box" not in _config):
        logging.warning(
            "\tLand mask filter is enabled but no geometry/bounds is given. Filter will be ignored from now on."
        )
        _config["land_mask"] = False
    if _config["land_mask"] and _seas_tree == []:
        if "geometry_file_path" in _config:
            logging.warning("\tLoading sea geometries.")
            seas = load_geom(_config, out_crs=out_crs)
            logging.warning("\tLoaded geometries for land mask.")
            for _, sea in seas.iterrows():
                polygons = shape(sea["geometry"])
                for _polygon in polygons.geoms:
                    seas_list += polygon_split(
                        make_valid(_polygon), threshold=grid_edge_length
                    )
        _seas_tree = STRtree(seas_list)
        logging.warning("\tLoaded land mask.\n")

    t_0 = time.time()
    stats_list = []
    futures = {}
    with ProcessPoolExecutor(
        max_workers=maxThreads,
        initializer=clean_init,
        initargs=(_config, _seas_tree, _project),
    ) as executor:
        for f in os.listdir(ais_file):
            if f.endswith(".csv"):
                file_mmsi = f.split("/")[-1].split(".")[-2]
                if fsizes.get(file_mmsi, minPos + 1) < minPos:
                    stats_list.append(
                        [fsizes.get(file_mmsi, 0), 0, 0, 0, 0, 0, 0, 0, 0, file_mmsi]
                    )
                    continue

                futures[executor.submit(clean_mmsi, (f.split(".")[0]))] = file_mmsi

        for future in as_completed(futures):
            try:
                res = future.result()
                res.append(futures[future])
                stats_list.append(res)
            except Exception as exc:
                logging.error("Thread exception (%s): %s" , futures[future], exc)

    logging.warning("\t\tCleaning time: %s",time.time() - t_0)
    stats_df = pd.DataFrame(
        stats_list,
        columns=[
            "total_rows",
            "output_rows",
            "rem_empty_fields",
            "rem_movement_fields",
            "rem_mmsi",
            "rem_land_mask",
            "rem_downsampling",
            "rem_noise",
            "rem_timeframe",
            "mmsi",
        ],
    )
    stats_df.set_index(["mmsi"], inplace=True)
    stats_df.to_csv(_config["ais_stats_path"] + "cleaning_stats.csv")

    logging.debug("\n")
    tstats = stats_df.sum()
    trows = tstats["total_rows"]
    
    if trows != 0:
        for column, value in tstats.iteritems():
            logging.debug("\t%s: %.2f %%" ,column, 100 * value / trows)
    else:
        logging.debug("\tEmpty files given. Exiting..")
    return stats_list


if __name__ == "__main__":
  
    import json

    config_file = open(sys.argv[1], "r",encoding="utf-8")
    CONFIG = json.load(config_file)
    clean_data(CONFIG)
