from urllib.request import urlopen
import json

def create_bitstream_table(db):
    with db as c:
        c.execute('''create table if not exists
            bsinfo (bitstream_id primary key, filename, os, arch,
            product_name, codebase, release, revision, 
            creation_date, checkout_date, size)
        ''')
        return

def add_bitstream_info(db, slicer_records_url):
    data = json.load(urlopen(slicer_records_url))
    records = data['data']
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
