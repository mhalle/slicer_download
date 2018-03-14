import sys
import sqlite3
from ua_parser import user_agent_parser


db = sqlite3.connect(sys.argv[1])


with db as cur:
    for row in db.execute('select useragent from uainfo'):
        ua = row[0]
        r = user_agent_parser.Parse(ua)
        # print(r)
        uainfo = r['user_agent']

        #print(user_agent_parser.PrettyUserAgent(uainfo['family'], 
        #uainfo['major'], uainfo['minor'], uainfo['patch']))

        osinfo = r['os']
        print(user_agent_parser.PrettyOS(osinfo['family'], 
        osinfo['major'], osinfo['minor'], osinfo['patch']))