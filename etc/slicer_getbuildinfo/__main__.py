import sys
import urllib.request, urllib.error, urllib.parse
import sqlite3
import json

InfoURLMethod = 'midas.slicerpackages.get.packages'
InfoURLBase = 'http://slicer.kitware.com/midas3/api/json'


def getMidasRecordsFromURL():
    infoURL = '{0}?productname=Slicer&method={1}'.format(InfoURLBase, InfoURLMethod)

    info = None

    fp = urllib.request.urlopen(infoURL)
    info = fp.read()
    fp.close()

    return json.loads(info)['data']


def recordToDb(r):
    try:
        return [int(r['item_id']),
                int(r['revision']),
                r['checkoutdate'],
                r['date_creation'],
                json.dumps(r)]
    except ValueError:
        return None


def main(dbfile):
    records = getMidasRecordsFromURL()
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


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage is: %s <dbfile>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
