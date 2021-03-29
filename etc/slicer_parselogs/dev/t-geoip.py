import sys
import sqlite3
import geoip2.database


db = sqlite3.connect(sys.argv[1])

geoip_reader = geoip2.database.Reader(sys.argv[2])
geoip_lookup = geoip_reader.city
with db as cur:
    for row in db.execute('select ip from access'):
        ip = row[0]
        try:
            r = geoip_lookup(ip)
        except geoip2.errors.AddressNotFoundError:
            continue
        try:
            subdiv = r.subdivisions[0].names['en']
        except (KeyError, IndexError):
            subdiv = None
        try:
            city = r.city.names['en']
        except:
            city = None
        print(r.country.iso_code, subdiv, city)
