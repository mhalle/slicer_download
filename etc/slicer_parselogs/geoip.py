import geoip2.database    


def create_geoip_table(db):
    with db as c:
        c.execute('''create table if not exists
            ipinfo (ip primary key, country_code, country_code3, country_name,
            region_name, city, latitude, longitude);
        ''')


def add_geoip_info(db, geoip_data_filename):

    geoip_reader = geoip2.database.Reader(geoip_data_filename)
    geoip_lookup = geoip_reader.city  # use the city database

    ipCompleted = set()
    for ip in list(db.execute("""select ip from access
                            except
                            select ip from ipinfo""")):
        ip = ip[0]
        if ip in ipCompleted:
            continue

        try:
            r = geoip_lookup(ip)
        except geoip2.errors.AddressNotFoundError:
            continue

        if r.location.latitude is None:
            continue
        
        try:
            subdivision = r.subdivisions[0].names['en']
        except (KeyError, IndexError):
            subdivision = None

        try:
            city = r.city.names['en']
        except (KeyError, IndexError):
            city = None

        try:
            country = r.country.names['en']
        except (KeyError, IndexError):
            country = None

        db.execute('''insert or replace into ipinfo(ip,
                                        country_code, country_code3, country_name,
                                        region_name, city, latitude, longitude)
                                        values(?, ?, ?, ?, ?, ?, ?, ?);''',
                                        (ip,
                                        r.country.iso_code,
                                        r.country.iso_code,  # was country_code3
                                        country,
                                        subdivision,
                                        city,
                                        float(r.location.latitude),
                                        float(r.location.longitude)))
        ipCompleted.add(ip)
        db.commit()  # commit per record in case we exit
    return
