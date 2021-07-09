import sys
import re
import gzip
import os
import apache_log_parser

from slicer_download import (
    getServerAPI,
    ServerAPI
)

bitstreamRE = {
    ServerAPI.Midas_v1: re.compile(r'/bitstream/(\d+)'),
    ServerAPI.Girder_v1: re.compile(r'/bitstream/([a-fA-F\d]{24})')
}


def create_access_table(db):
    "Initialize sqlite table for web access records."
    print("creating 'access' table")
    with db as c:
        c.execute('''create table if not exists
                access (bitstream_id, ip, ts, useragent)
                ''')

        c.execute('''create unique index if not exists access_unique_idx
                    on access(bitstream_id, ip, ts)''')


def add_access_info(db, filenames):
    """Add bitstream access information to sqlite table."""
    print("populating 'access' table")
    for access in read_and_parse(filenames):
        req = access['request_url_path']
        m = bitstreamRE[getServerAPI()].match(req)
        if not m:
            continue

        host = access['remote_ip']
        user_agent = access['request_header_user_agent']
        access_time = access['time_received_utc_isoformat']
        bitstream_id = m.group(1)
        db.execute("""insert or ignore into access(bitstream_id, ip, ts, useragent)
                    values(?, ?, ?, ?)""",
                    (bitstream_id, host, access_time, user_agent))
    db.commit()


def read_and_parse(filenames):
    """Read all apache log files (possibly gzipped) and 
       yield each parsed bitsteam download event."""
    log_parser = create_log_parser()
    for filename in filenames:
        print("parsing '{0}'".format(filename))

        if os.path.splitext(filename)[1] == '.gz':
            fp = gzip.open(filename, 'rt')
        else:
            fp = open(filename)
        for line in fp:
            if not bitstreamRE[getServerAPI()].search(line):
                # if no bitstream ID, don't go any further
                continue
            try:
                p = log_parser(line)
            except apache_log_parser.LineDoesntMatchException:
                print("failed to parse '{0}'".format(line), file=sys.stderr)
                continue
            yield p


def create_log_parser():
    "Create parser for apache log entries (webfaction default)"
    # apache config:
    # %{X-Forwarded-For}i %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"
    format_string = r'%a %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"'
    log_parser = apache_log_parser.make_parser(format_string)
    return log_parser
