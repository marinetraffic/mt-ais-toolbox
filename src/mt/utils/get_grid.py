import json
import time
import fiona

import geopandas as gpd
from shapely.geometry import Polygon, shape
from shapely.validation import make_valid


from mt.utils.outputFileUtils import check_if_path_exists, generate_dictionary_IfNotExists
from mt.utils.auxiliary import polygon_split


def load_grids(config):
    gdf = None
    seas_gdf = None
    out_crs = config.get("out_crs", 3035)
    splitThres = config.get("polygon_split_threshold", config["grid_edge_lengths"][-1])

    gridsDict = {}
    for grid_edge_length in config["grid_edge_lengths"]:

        dirName = "%s" % config["grids_path"]
        generate_dictionary_IfNotExists(dirName)
        dataFilePath = "%sgridsWithSea_%d_%d.json" % (dirName, out_crs, grid_edge_length)

        if check_if_path_exists(dataFilePath):
            print(
                "\tFound already extracted grid. In case you need a different geometry or bounds delete/move the grid file from the Grids dictionary.\n\tLoading data from %s"
                % dataFilePath
            )
            gridsWithSea = gpd.read_file(dataFilePath)
        else:

            if gdf is None:
                print("\tLoading sea geometries")

                if "geometry_file_path" in config:
                    gdf = load_geom(config, out_crs=out_crs)
                    [minLon, minLat, maxLon, maxLat] = gdf.total_bounds

                if "bounding_box" in config:
                    [minLon, minLat, maxLon, maxLat] = config["bounding_box"]
                    maxLon -= 1
                    maxLat -= 1
                elif "geometry_file_path" not in config:
                    print("\tNo bound and no geometry given.\n\tExiting..")
                    exit()

            print(
                "\tGenerating Grids for grid_edge_length: %.1fkm"
                % (grid_edge_length / 1000)
            )
            [minX, minY, maxX, maxY] = [
                int(minLon / grid_edge_length),
                int(minLat / grid_edge_length),
                int(maxLon / grid_edge_length),
                int(maxLat / grid_edge_length),
            ]
            print("\tBoundaries:", [minX, minY, maxX, maxY])
            t_0 = time.time()
            grids = []
            for x in range(minX, maxX + 1):
                for y in range(minY, maxY + 1):
                    polygon = Polygon(
                        [
                            (x * grid_edge_length, y * grid_edge_length),
                            ((x + 1) * grid_edge_length, y * grid_edge_length),
                            ((x + 1) * grid_edge_length, (y + 1) * grid_edge_length),
                            (x * grid_edge_length, (y + 1) * grid_edge_length),
                            (x * grid_edge_length, y * grid_edge_length),
                        ]
                    )
                    grids.append(
                        {
                            "x": x,
                            "y": y,
                            "gridID": "%d_%d" % (x, y),
                            "geometry": polygon,
                        }
                    )

            gridsGDF = gpd.GeoDataFrame(grids)
            gridsGDF.set_crs(epsg=out_crs, inplace=True)
            print("\tGenerated %d cells" % len(gridsGDF))
            print("\t\tExec. time: %1.fsec\t" % (time.time() - t_0))

            if gdf is not None:
                if seas_gdf is None:
                    seas_list = []
                    for _, sea in gdf.iterrows():
                        polygons = shape(sea["geometry"])
                        for _polygon in polygons.geoms:
                            seas_list += polygon_split(
                                make_valid(_polygon), threshold=splitThres
                            )
                    seas_gdf = gpd.GeoDataFrame(
                        seas_list, columns=["geometry"]
                    ).set_crs(out_crs, inplace=True)

                t_0 = time.time()
                gridsWithSea = gpd.sjoin(gridsGDF, seas_gdf, how="inner")
                gridsWithSea.drop(columns=["index_right"], inplace=True)
                print("\tIntersected sea geometries with the grids.")
                print("\t\tExec. time: %1.fsec\t" % (time.time() - t_0))
            elif "bounding_box" in config:
                gridsWithSea = gridsGDF

            gridsWithSea.to_file(dataFilePath, driver="GeoJSON")
            print("\tSaved grid in %s." % dataFilePath)

        gridsDict[grid_edge_length] = gridsWithSea
    return gridsDict


def load_geom(config, out_crs=3035):
    fend = config["geometry_file_path"].split(".")[-1]
    if fend == "gdb" or fend == "gpkg":
        layers = fiona.listlayers(config["geometry_file_path"])
        gdf = gpd.read_file(
            config["geometry_file_path"], driver="FileGDB", layer=layers[0]
        )
    else:
        gdf = gpd.read_file(config["geometry_file_path"])

    if gdf.crs == None:
        gdf.set_crs(out_crs, inplace=True)
    elif gdf.crs.to_epsg() != out_crs:
        gdf.to_crs(out_crs, inplace=True)

    return gdf


if __name__ == "__main__":
    import sys
    import json

    config_file = open(sys.argv[1], "r")
    config = json.load(config_file)

    load_grids(config)
