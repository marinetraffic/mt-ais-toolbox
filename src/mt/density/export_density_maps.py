
"""_summary_
"""
import sys
import json
import time

import os
import subprocess
from pathlib import Path

from mt.density.get_density import get_density

class RasterConverter:
    """Class that wraps GDAL functionality to convert to csv to raster files for the EU region in 3035 projection system.
    """
    def __init__(self) -> None:
        pass

    def csv_to_tiff(
        self,
        path,
        filename,
        columns,
        step,
        srs="EPSG:3035",
        extent="-123056.687087586, 756321.594840121, 6883384.9426963, 7369716.25546598",
        no_data=-9999,
        colors_path=None,
    ):
        """
           csv to raster function.     
        """

        original_pwd = os.getcwd()
        colors_path_absolute = f"{os.path.join(original_pwd,colors_path)}/colors_{step}.txt"
        print(original_pwd)
        try:

            geometry_bound = [943609.7539, -375446.0312, 7601958.5, 6825119.3209]
            geometry_bound = [int(x / step) * step for x in geometry_bound]

            os.chdir(path)
            clean_filename = filename.split(".")[0]
            for col in columns:
                vrt_context = f"""
                        <OGRVRTDataSource>
                                <OGRVRTLayer name="{clean_filename}">
                                        <SrcDataSource>{clean_filename}.csv</SrcDataSource>
                                        <GeometryType>wkbPoint</GeometryType>
                                        <GeometryField encoding="PointFromColumns" x="lon_centroid" y="lat_centroid" z="{col}"/>
                                </OGRVRTLayer>
                        </OGRVRTDataSource>
                            """

                with open(Path(f"{filename[:-4]}.vrt"), "w",encoding='utf-8') as f:
                    f.write(vrt_context)

                cmd = f"gdal_rasterize -tr {step} {step} -a_nodata {no_data} -te {str(geometry_bound)[1:-1]} -a_srs {srs} -ot Float32 -a {col} {filename[:-4]}.vrt {filename[:-4]}.tif"
                print(cmd)
                subprocess.call(cmd, shell=True)
                if os.path.exists(colors_path_absolute):
                    cmd = f"gdaldem color-relief {filename[:-4]}.tif {colors_path_absolute} {filename[:-4]}_colored.tif -alpha"
                    subprocess.call(cmd, shell = True)
                    os.remove(f"{filename[:-4]}.tif")
                os.remove(f"{filename[:-4]}.vrt")
        finally:
            os.chdir(original_pwd)


def export_denity_map(_config, infile=""):
    """_summary_

    Args:
        config (_type_): _description_
        infile (str, optional): _description_. Defaults to "".
    """
    
    
    if infile == "":
        infile = _config["ais_cleaned_path"]
    outCRS = str(_config.get('out_crs', 3035))
    colors_path = _config.get('colors_files_path', None)

    for gridEL in _config.get("grid_edge_lengths", [10000]):
        print('\tCalculating density for grid cell size: '+str(gridEL))
        # Estimating & saving time at cells
        resTypes, _respath = get_density(_config, gridEdgeLength=gridEL, ais_files_path=infile)
        print('\tCreating map files for grid cell size: '+str(gridEL))
        for vType in resTypes:
            respath = _respath+'_'+vType+'.csv'
            # Generating TIF file
            RasterConverter().csv_to_tiff(
                "/".join(respath.split("/")[:-1]),
                respath.split("/")[-1],
                ["density"],
                gridEL,
                srs="EPSG:"+outCRS,
                colors_path=colors_path,
            )


# INPUT: 1->config 2->input file, 3->emodnet
if __name__ == "__main__":
    
    config_file = open(sys.argv[1], "r",encoding='utf-8')
    config = json.load(config_file)



    #print("Creating density maps for " + out_name)
    t_0 = time.time()
    export_denity_map(config, "")
    print(time.time() - t_0)


# EXTEND SHOULD BE
# aligned with int(geometry (coastline) bounds / (gridedgelength) ) * gridedgelength
# geometry bound = array([ 943609.7539, -375446.0312, 7601958.5   , 6825119.3209])
# e.g. gdal extend for 100k => 900000, -300000, 7600000, 6800000