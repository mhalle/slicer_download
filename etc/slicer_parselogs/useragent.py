from ua_parser import user_agent_parser


def create_useragent_table(db):
    with db as c:
        c.execute('''create table if not exists
            uainfo (useragent primary key, 
                    browser_type, ua_name, os_name, os_family)
        ''')


def get_browser_type_compat(rec):
    family = rec['device']['family']

    if family == 'Spider':
        return 'Robot'
    if family == 'Other':
        return 'Browser'
    return 'MobileBrowser'


def pretty_os(rec):
    os = rec['os']
    return user_agent_parser.PrettyOS(os['family'],
                                      os['major'],
                                      os['minor'],
                                      os['patch'])


def add_useragent_info(db):
    ua_completed = set()
    for ua in list(db.execute("""select useragent from access
                            except
                            select useragent from uainfo""")):
        user_agent = ua[0]
        if user_agent in ua_completed:
            continue
        ua_rec = user_agent_parser.Parse(str(ua))
        if not ua_rec:
            continue

        db.execute("""insert or replace into uainfo(useragent,
                    browser_type, ua_name, os_name, os_family) 
                    values(?, ?, ?, ?, ?)""",
                    (user_agent,
                     get_browser_type_compat(ua_rec),
                     ua_rec['user_agent']['family'],
                     pretty_os(ua_rec),
                     ua_rec['os']['family']))
        ua_completed.add(user_agent)
        db.commit() # commit per record in case we exit
    return
