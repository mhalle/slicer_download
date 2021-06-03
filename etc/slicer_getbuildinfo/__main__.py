import json
import os
import urllib.error
import urllib.parse
import urllib.request
import sqlite3
import sys
import textwrap

from enum import Enum


class ServerAPI(Enum):
    Midas_v1 = 1


def getServerAPI():
    return ServerAPI[os.getenv("SLICER_DOWNLOAD_SERVER_API", ServerAPI.Midas_v1.name)]


def getServerAPIUrl():
    return {
        ServerAPI.Midas_v1: "http://slicer.kitware.com/midas3/api/json",
    }[getServerAPI()]


def getMidasRecordsFromURL():
    InfoURLMethod = 'midas.slicerpackages.get.packages'

    infoURL = '{0}?productname=Slicer&method={1}'.format(getServerAPIUrl(), InfoURLMethod)

    fp = urllib.request.urlopen(infoURL)
    info = fp.read()
    fp.close()

    return json.loads(info)['data']


def getRecordsFromURL():
    return {
        ServerAPI.Midas_v1: getMidasRecordsFromURL,
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


def recordToDb(r):
    return {
        ServerAPI.Midas_v1: midasRecordToDb,
    }[getServerAPI()](r)


def main(dbfile):

    print("ServerAPI is {0}: {1}".format(getServerAPI().name, getServerAPIUrl()))

    records = getRecordsFromURL()
    with sqlite3.connect(dbfile) as db:
        db.execute('''create table if not exists
        _(item_id INTEGER primary key,
                    revision INTEGER,
                    checkout_date TEXT,
                    build_date TEXT,
                    record TEXT)''')

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
