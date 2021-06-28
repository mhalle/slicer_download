from slicer_download import (
    getServerAPI,
    ServerAPI
)


def create_bitstream_table(db):
    print("creating 'bsinfo' table")
    with db as c:
        c.execute('''create table if not exists
            bsinfo (bitstream_id primary key, filename, os, arch,
            product_name, codebase, release, revision, 
            creation_date, checkout_date, size)
        ''')
        return


def add_bitstream_info(db, records):
    print("populating 'bsinfo' table")
    if getServerAPI() == ServerAPI.Girder_v1:
        return
    for r in records:
        bs = r['bitstreams'][0]
        db.execute("""
            insert or replace into bsinfo(
                bitstream_id, filename, os, arch,
                product_name, codebase, release,
                revision, creation_date,
                checkout_date, size)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (bs['bitstream_id'],
                 bs['name'],  # filename
                 r['os'],
                 r['arch'],
                 r['productname'], # product_name
                 r['codebase'],
                 r.get('release', ''),
                 r['revision'],
                 r['date_creation'], #creation_date
                 r['checkoutdate'],  #checkout_date
                 bs['size']))
        db.commit()
    return
