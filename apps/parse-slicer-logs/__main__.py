import sys
import os


def absPath(*args):
    here = os.path.split(__file__)[0]
    return os.path.join(here, *args);

sys.path.append(absPath('modules'))

import re
from uasparser2 import UASParser
import apachelog
import pygeoip

import sqlite3
import datetime, time
import urllib2
import json
from pprint import pprint
import os.path
import gzip


IPDataFile = absPath('data', 'GeoLiteCity.dat')

bitstreamRE = re.compile(r'GET /bitstream/(\d+)')
MidasSlicerInfoURL = \
 "http://slicer.kitware.com/midas3/api/rest/?method=midas.slicerpackages.get.packages&format=json"

class Timezone(datetime.tzinfo):
    def __init__(self, name="+0000"):
        self.name = name
        seconds = int(name[:-2])*3600+int(name[-2:])*60
        self.offset = datetime.timedelta(seconds=seconds)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.name

def parseApacheTimestamp(t):
    tt = time.strptime(t[:-6], "%d/%b/%Y:%H:%M:%S")
    tt = list(tt[:6]) + [ 0, Timezone(t[-5:]) ]
    return datetime.datetime(*tt).isoformat()


def createTables(conn):
    c = conn.cursor()
    c.execute('''create table if not exists
                access (bitstream_id, ip, ts, useragent);
    ''')

    c.execute('''create unique index if not exists access_unique_idx
                    on access(bitstream_id, ip, ts);''')

    c.execute('''create table if not exists
                uainfo (useragent primary key, browser_type, ua_name, os_name, os_family);
    ''')

    c.execute('''create table if not exists
                ipinfo (ip primary key, country_code, country_code3, country_name,
                        region_name, city, latitude, longitude);
    ''')

    c.execute('''create table if not exists
                bsinfo (bitstream_id primary key, filename, os, arch,
                product_name, codebase, release, revision, creation_date, checkout_date, size);
    ''')

    conn.commit()
    c.close()

def unicodeOrNone(x):
    return unicode(x, errors='replace') if x else None

def dictUnicodeOrNone(d, key):
    try:
        x = d[key]
    except KeyError:
        return None

    return x if x else None

def outputToFile(filename, data, columns=None):
    fp = open(filename, 'w')

    if columns:
        fp.write('%s\t%s\n' % (columns[0], columns[1]))
    for x, y in data:
        fp.write('%s\t%d\n' % (x, y))
    fp.close()


def readAndParse(filenames):
    p = apachelog.parser(apachelog.formats['extended'])
    for filename in filenames:

        if os.path.splitext(filename)[1] == '.gz':
            fp = gzip.open(filename, 'rb')
        else:
            fp = open(filename)


        for line in fp:
            if not bitstreamRE.search(line):
                # if no bitstream ID, don't go any further
                continue
            try:
                data = p.parse(line)
            except apachelog.ApacheLogParserError:
                print >> sys.stderr, "failed to parse", line,
                continue

            yield dict(requestor=data['%h'],
                       bytes=data['%b'],
                       request=data['%r'],
                       time=data['%t'].strip('[]'),
                       user=data['%u'],
                       result=data['%>s'],
                       useragent=data['%{User-agent}i'],
                       referer=data['%{Referer}i'])


class KO(object):
    pass

def addBitstreamInfo(db):
    data = json.load(urllib2.urlopen(MidasSlicerInfoURL))
    records = data['data']
    o = KO()
    for r in records:
        bs = r['bitstreams'][0]
        o.os = r['os']
        o.arch = r['arch']
        o.revision = r['revision']
        o.release = r.get('release', '')
        o.bitstream_id = bs['bitstream_id']
        o.filename = bs['name']
        o.size = bs['size']
        o.creation_date = r['date_creation']
        o.checkout_date = r['checkoutdate']
        o.codebase = r['codebase']
        o.product_name = r['productname']
        db.execute("""
            insert or replace into bsinfo(
                bitstream_id, filename, os, arch,
                product_name, codebase, release,
                revision, creation_date,
                checkout_date, size)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (o.bitstream_id, o.filename, o.os, o.arch,
                 o.product_name, o.codebase, o.release, o.revision,
                 o.creation_date, o.checkout_date, o.size))
        db.commit()
    return


def parseApacheLogs(db, filenames):
    for access in readAndParse(filenames):
        req = access['request']
        m = bitstreamRE.match(req)
        if not m:
            continue

        host = access['requestor']
        userAgent = access['useragent']
        accessTime = parseApacheTimestamp(access['time'])
        bitstreamId = m.group(1)
        db.execute("""insert or ignore into access(bitstream_id, ip, ts, useragent)
                    values(?, ?, ?, ?)""",
                    (bitstreamId, host, accessTime, userAgent))
    db.commit()

def addGeoIPInfo(db):
    # geoip = GeoIP.open(IPDataFile, GeoIP.GEOIP_STANDARD)
    geoip = pygeoip.GeoIP(IPDataFile);

    ipCompleted = set()
    for ip in list(db.execute("""select ip from access
                            except
                            select ip from ipinfo""")):
        ip = ip[0]
        if ip in ipCompleted:
            continue
        r = geoip.record_by_addr(ip)
        if not r:
            continue
        db.execute('''insert or replace into ipinfo(ip,
                                        country_code, country_code3, country_name,
                                        region_name, city, latitude, longitude)
                                        values(?, ?, ?, ?, ?, ?, ?, ?);''',
                                        (ip,
                                        dictUnicodeOrNone(r, 'country_code'),
                                        dictUnicodeOrNone(r, 'country_code3'),
                                        dictUnicodeOrNone(r, 'country_name'),
                                        dictUnicodeOrNone(r, 'metro_code'),
                                        dictUnicodeOrNone(r, 'city'),
                                        float(r['latitude']),
                                        float(r['longitude'])))
        ipCompleted.add(ip)
        db.commit() # commit per record in case we exit
    return

def addUserAgentInfo(db):
    uas_parser = UASParser('/tmp', mem_cache_size=1000, cache_ttl=3600*24*7)
    uaCompleted = set()
    for ua in list(db.execute("""select useragent from access
                            except
                            select useragent from uainfo""")):
        userAgent = ua[0]
        if userAgent in uaCompleted:
            continue
        uaRec = uas_parser.parse(userAgent)
        if not uaRec:
            continue
        db.execute("""insert or replace into uainfo(useragent,
                    browser_type, ua_name, os_name, os_family) values(?, ?, ?, ?, ?)""",
                    (userAgent, uaRec['typ'], uaRec['ua_name'],
                     uaRec['os_name'], uaRec['os_family']))
        uaCompleted.add(userAgent)
        db.commit() # commit per record in case we exit
    return


if __name__ == '__main__':
    dbname = sys.argv[1]
    filenames = sys.argv[2:]
    db = sqlite3.connect(dbname)
    createTables(db)

    # parse apache logs, if they exist
    parseApacheLogs(db, filenames)

    addBitstreamInfo(db)
    # then geolocate based on IPs
    addGeoIPInfo(db)

    # then parse user agents
    addUserAgentInfo(db)
    db.close()
    sys.exit(0)

