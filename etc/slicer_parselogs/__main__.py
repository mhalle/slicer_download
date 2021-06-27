import argparse
import json
import sqlite3
import sys

from slicer_parselogs import (
    access,
    bitstream,
    geoip,
    useragent,
    slicerstats
)

SlicerMidasRecordsURL = \
 "http://slicer.kitware.com/midas3/api/rest/?method=midas.slicerpackages.get.packages&format=json"


def main():
    argparser = argparse.ArgumentParser(description='Process Slicer4 download information.')
    argparser.add_argument('--db', required=True, help="sqlite stats database")
    argparser.add_argument('--geoip', required=True, help="geoip data file")
    argparser.add_argument('--statsdata', required=True, help="slicer stats output")
    argparser.add_argument('--nomidas', action='store_true', help="don't download midas data")
    argparser.add_argument('filenames', nargs="*")
    args = argparser.parse_args()
    dbname = args.db
    geoip_filename = args.geoip
    filenames = args.filenames
    statsdata = args.statsdata

    db = sqlite3.connect(dbname)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    access.create_access_table(db)
    bitstream.create_bitstream_table(db)
    geoip.create_geoip_table(db)
    useragent.create_useragent_table(db)

    # parse apache logs, if they exist, and add them to db
    access.add_access_info(db, filenames)

    # each of these items depends on the access table
    geoip.add_geoip_info(db, geoip_filename)
    useragent.add_useragent_info(db)
    if not args.nomidas:
        bitstream.add_bitstream_info(db, SlicerMidasRecordsURL)

    # then write out slicer json

    slicer_stats_data = slicerstats.get_download_stats_data(db)
    with open(statsdata, 'w+') as statsfp:
        json.dump(slicer_stats_data, statsfp, separators=(',', ':'))

    db.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
