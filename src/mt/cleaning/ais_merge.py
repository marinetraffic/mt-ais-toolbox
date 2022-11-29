"""_summary_
"""
import os
import bz2
import csv
import json
# import logging
# from errno import ENOMSG
# from tarfile import ENCODING

# INPUT: t, station, channel_code, mmsi, type, data_type, data



def merge_pos_and_static(in_names, out_name, stats_name):
    """
        It binds possitional messages with static information of
        earlier messages. It requires a set csv time ordered csv files.
        Each message contains a decoded NMEA message with the following format:

        INPUT: t, station, channel_code, mmsi, type, data_type, data

        Given the 'type' of each message the data field contains one of the following lists:

        STATIC: t,station,channel_code,mmsi,type,data_type,imo;
                      shiptype;to_bow;to_stern;to_port;to_starboard;callsign;shipname;
                      draught;destination;eta_month;eta_day;eta_hour;eta_minute
        POSITIONAL: t,station,channel_code,mmsi,type,data_type,
                      lon;lat;heading;course;speed;rot_direction;rot;navigation_status

        For more information about the NMEA message types and relevant information
        please refer to https://navcen.uscg.gov/?pageName=AISMessages

	    Usage:
            python -m src.mt.cleaning.ais_merge \
                'PATH/TO/DECODED/DATA/*.csv.bz2'\
                 PATH/TO/OUTPUT/FOLDER/\
                 PATH/TO/STATISTICS/FOLDER

    Args:
        in_names (string): path to decoded data.It supports plain text csv
                            files and bz2 compressed files.
        out_name (_type_): the destination folder path.
        stats_name (_type_): the statistics folder path. TODO: describe statistics.
    """

    _sd = {}  # static data dictionary
    out_files = {}

    count = {}

    for in_name in in_names:
        with bz2.open(in_name, "rt") if in_name.endswith(".bz2") else open(in_name,encoding='utf-8') as in_file:
            next(in_file)
            for line in in_file:
                row = next(csv.reader([line], doublequote=False, escapechar="\\"))
                data = next(csv.reader([row[6]], delimiter=";"))

                if row[5] == "0":  # static data
                    if data[1]:
                        _sd[row[3]] = data[1]  # shiptype
                else:
                    # Calculate AIS message class
                    mtype = int(row[4])
                    if mtype == 1 or mtype == 2 or mtype == 3 or mtype == 27:
                        vclass = "A"
                    else:
                        vclass = "B"

                    # Get output file descriptor / open file for writing
                    file_f = out_files.get(row[3])
                    if file_f is None:
                        file_f = open(os.path.join(out_name,row[3] + ".csv"), "w",encoding='utf-8')
                        file_f.write(
                            "TIMESTAMP,MMSI,LON,LAT,HEADING,COURSE,SPEED,NAVIGATIONAL_STATUS,TYPE,STATION,CLASS\n"
                        )
                        out_files[row[3]] = file_f
                        count[row[3]] = 0

                    file_f.write(
                        f'{row[0]},{row[3]},{data[0]},{data[1]},{data[2]},{data[3]},{data[4]},{data[7]},{_sd.get(row[3], "")},{row[1]},{vclass}\n'
                    )
                    count[row[3]] += 1
    cout = open(os.path.join(stats_name , "merging_stats.json"), "w",encoding="utf-8")
    json.dump(count, cout)


if __name__ == "__main__":
    import sys
    import glob
    import psutil

    p = psutil.Process()
    soft, hard = p.rlimit(psutil.RLIMIT_NOFILE)
    p.rlimit(psutil.RLIMIT_NOFILE, (hard, hard))
    
    config_file = open(sys.argv[1], "r",encoding="utf-8")
    CONFIG = json.load(config_file)
    
    ais_decode_path = CONFIG["ais_decoded_path"]
    merged_path = CONFIG["ais_path"]
    stats_path = CONFIG["ais_stats_path"]
    
    merge_pos_and_static(
        sorted([y for x in sys.argv[1].split(",") for y in glob.glob(ais_decode_path)]),
        merged_path,
        stats_path,
    )
