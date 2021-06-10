import json
import os
import urllib.error
import urllib.parse
import urllib.request
import requests
import sqlite3
import sys
import textwrap

from enum import Enum


class ServerAPI(Enum):
    Midas_v1 = 1
    Girder_v1 = 2


def getServerAPI():
    return ServerAPI[os.getenv("SLICER_DOWNLOAD_SERVER_API", ServerAPI.Midas_v1.name)]


def getServerAPIUrl():
    return {
        ServerAPI.Midas_v1: "http://slicer.kitware.com/midas3/api/json",
        ServerAPI.Girder_v1: "https://slicer-packages.kitware.com/api/v1",
    }[getServerAPI()]


def getMidasRecordsFromURL():
    InfoURLMethod = 'midas.slicerpackages.get.packages'

    infoURL = '{0}?productname=Slicer&method={1}'.format(getServerAPIUrl(), InfoURLMethod)

    fp = urllib.request.urlopen(infoURL)
    info = fp.read()
    fp.close()

    return json.loads(info)['data']


def getGirderRecordsFromURL():
    result = requests.get("{0}/app/5f4474d0e1d8c75dfc705482/package?limit=0".format(getServerAPIUrl()))
    return result.json()


def getRecordsFromURL():
    return {
        ServerAPI.Midas_v1: getMidasRecordsFromURL,
        ServerAPI.Girder_v1: getGirderRecordsFromURL,
    }[getServerAPI()]()


def midasRecordToDb(r):
    try:
        return [int(r['item_id']),
                int(r['revision']),
                r['checkoutdate'],
                r['date_creation'],
                json.dumps(r)]
    except ValueError:
        return None


def girderRecordToDb(r):
    return [r['_id'],
            int(r['meta']['revision']),
            r['created'],
            r['meta']['build_date'],
            json.dumps(r)]


def recordToDb(r):
    return {
        ServerAPI.Midas_v1: midasRecordToDb,
        ServerAPI.Girder_v1: girderRecordToDb,
    }[getServerAPI()](r)


def main(dbfile):

    print("ServerAPI is {0}: {1}".format(getServerAPI().name, getServerAPIUrl()))

    records = getRecordsFromURL()

    primary_key_type = "INTEGER" if getServerAPI() == ServerAPI.Midas_v1 else "TEXT"

    with sqlite3.connect(dbfile) as db:
        db.execute('''create table if not exists
        _(item_id {primary_key_type} primary key,
                    revision INTEGER,
                    checkout_date TEXT,
                    build_date TEXT,
                    record TEXT)'''.format(primary_key_type=primary_key_type))

        cursor = db.cursor()
        cursor.executemany('''insert or ignore into _
            (item_id, revision, checkout_date, build_date, record)
            values(?,?,?,?,?)''',
                           [_f for _f in (recordToDb(r) for r in records) if _f])
        db.commit()

    print("Retrieved {0} records".format(len(records)))
    print("Saved {0}".format(dbfile))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(textwrap.dedent("""
        Usage: %s DB_FILE

          Download Slicer application package metadata and update sqlite database

        """ % sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    main(sys.argv[1])
