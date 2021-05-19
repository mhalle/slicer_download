import flask
from flask import json

import re
import os
import sqlite3

from itertools import groupby, islice

SupportedOSChoices = ('macosx', 'win', 'linux')
StabilityChoices = ('release', 'nightly', 'any')
ModeChoices = ('revision', 'closest-revision',
               'version', 'checkout-date', 'date')

DownloadURLBase = 'https://slicer.kitware.com/midas3/download'
LocalBitstreamPath = '/bitstream'

app = flask.Flask(__name__)
app.config.from_envvar('SLICER_DOWNLOAD_SERVER_CONF')


@app.route('/')
def downloadPage():
    allRecords, error_message, error_code = recordsMatchingAllOSAndStability()

    return flask.render_template('download.html', R=allRecords)


@app.route('/bitstream/<bitstreamId>')
def redirectToSourceBitstream(bitstreamId):
    midasBitstreamURL = '{0}?bitstream={1}'.format(DownloadURLBase, bitstreamId)
    return flask.redirect(midasBitstreamURL)


@app.route('/download')
def redirectToLocalBitstream():
    record, error_message, error_code = recordMatching()

    if record:
        return flask.redirect(record['download_url'])

    if error_code in (400, 404):
        return flask.render_template('{0}.html'.format(error_code), error_message=error_message), error_code

    flask.abort(error_code)


@app.route('/find')
def recordFindRequest():
    record, error_message, error_code = recordMatching()

    if record:
        return json.dumps(record)

    if error_code in (400, 404):
        return flask.render_template('{0}.html'.format(error_code), error_message=error_message), error_code

    flask.abort(error_code)


@app.route('/findall')
def recordFindAllRequest():
    allRecords, error_message, error_code = recordsMatchingAllOSAndStability()

    if allRecords:
        return json.dumps(allRecords)

    if error_code in (400, 404):
        return flask.render_template('{0}.html'.format(error_code), error_message=error_message), error_code

    flask.abort(error_code)


def cleanupMidasRecord(r):
    """Convert a raw MIDAS record into something a little bit more useful,
    including new fields and more consistent names."""
    if not r:
        return None
    d = {}
    for field in ('arch', 'revision', 'os', 'codebase', 'name', 'package'):
        d[field] = r[field]
    d['build_date'] = r['date_creation']
    d['build_date_ymd'] = d['build_date'].split(' ')[0]
    d['checkout_date'] = r['checkoutdate']
    d['checkout_date_ymd'] = d['checkout_date'].split(' ')[0]

    d['product_name'] = r['productname']
    d['stability'] = 'release' if r['release'] else 'nightly'
    d['size'] = r['bitstreams'][0]['size']
    d['md5'] = r['bitstreams'][0]['md5']
    d['version'] = getVersion(r)
    d['download_url'] = getLocalBitstreamURL(r)
    return d


def getLocalBitstreamURL(r):
    """Given a record, return the URL of the local bitstream
    (e.g., https://download.slicer.org/bitstream/XXXXX )"""
    bitstreamId = r['bitstreams'][0]['bitstream_id']

    downloadURL = '{0}/{1}'.format(LocalBitstreamPath, bitstreamId)
    return downloadURL


def recordMatching():
    """High level function for getting all records matching specific criteria including OS."""
    request = flask.request
    revisionRecords = getRecordsFromDb()

    os = request.args.get('os')  # may generate BadRequest if not present
    if os not in SupportedOSChoices:
        return None, 'unknown os "{0}": should be one of {1}'.format(os, SupportedOSChoices), 400

    offset = int(request.args.get('offset', '0'))

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value is not None:
            modeDict[name] = value

    if len(list(modeDict.keys())) == 0:
        modeName = 'date'
        value = '9999-12-31'  # distant date to force last record
    elif len(list(modeDict.keys())) == 1:
        modeName, value = list(modeDict.items())[0]
    else:
        return None, "invalid or ambiguous mode: should be one of {0}".format(ModeChoices), 400

    defaultStability = 'any' if modeName == 'revision' else 'release'
    stability = request.args.get('stability', defaultStability)

    if stability not in StabilityChoices:
        return None, "bad stability {0}: should be one of {1}".format(stability, StabilityChoices), 400

    r = getBestMatching(revisionRecords, os, stability, modeName, value, offset)
    c = cleanupMidasRecord(r)

    if not c:
        return None, "no matching revision for given parameters", 404

    return c, None, 200


def recordsMatchingAllOSAndStability():
    """High level function returning all records matching search criteria,
    for all OS and stability choices."""

    request = flask.request
    revisionRecords = getRecordsFromDb()

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value is not None:
            modeDict[name] = value

    offset = int(request.args.get('offset', '0'))

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value is not None:
            modeDict[name] = value

    if len(list(modeDict.keys())) == 0:
        modeName = 'date'
        value = '9999-12-31'  # distant date to force last record
    elif len(list(modeDict.keys())) == 1:
        modeName, value = list(modeDict.items())[0]
    else:
        return None, "invalid or ambiguous mode: should be one of {0}".format(ModeChoices), 400

    results = {}
    for os in SupportedOSChoices:
        osResult = {}
        for stability in ('release', 'nightly'):
            r = getBestMatching(revisionRecords, os, stability, modeName, value, offset)
            osResult[stability] = cleanupMidasRecord(r)
        results[os] = osResult

    return results, None, 200


# query matching functions
def matchOS(os):
    return lambda r: r['os'] == os


def matchExactRevision(rev):
    def match(r):
        return int(rev) == int(r['revision'])
    return match


def matchClosestRevision(rev):
    def match(r):
        return int(rev) >= int(r['revision'])
    return match


def matchDate(dt, dateType):
    def match(r):
        if dateType == 'date':
            dateString = r['date_creation']
        elif dateType == 'checkout-date':
            dateString = r['checkoutdate']
        if not dateString:
            return False
        justDateString = dateString.split(' ')[0]  # drop time
        return dt >= justDateString

    return match


def matchVersion(version):
    def match(r):
        rv = getVersion(r)
        if not rv:
            return False
        rvs = rv.split('.')
        vs = version.split('.')
        for i in range(0, len(vs)):
            if rvs[i] != vs[i]:
                return False
        return True
    return match


def matchStability(s):
    if s == 'nightly':
        return lambda r: r['submissiontype'] == 'nightly'
    if s == 'release':
        return lambda r: r['release'] != ""

    return lambda r: True

# composite field getters

# this looks ugly because we need to be able to accept versions like:
# 4.5.0, 4.5.0-1, 4.5.0-rc2, 4.5.0-gamma, and so forth


VersionWithDateRE = re.compile(r'^[A-z]+-([-\d.a-z]+)-(\d{4}-\d{2}-\d{2})')
VersionRE = re.compile(r'^[A-z]+-([-\d.a-z]+)-(macosx|linux|win+)')


def getVersion(record):
    if record['release']:
        return record['release']
    m = VersionWithDateRE.match(record['name'])
    if not m:
        m = VersionRE.match(record['name'])
    if not m:
        return None
    return m.group(1)


def getBitstreamInfo(r):
    return r['bitstreams'][0]


def allPass(predlist):
    """returns a function that evaluates each predicate in a list given an argument,
    and returns True if all pass, otherwise False."""
    def pred(x):
        for p in predlist:
            if not p(x):
                return False
        return True
    return pred


def getBestMatching(revisionRecords, os, stability, mode, modeArg, offset):
    osRecords = list(filter(matchOS(os), revisionRecords))

    selectors = [matchStability(stability)]

    # now, do either version, date, or revision
    if mode == 'version':
        selectors.append(matchVersion(modeArg))
    elif mode == 'revision':
        selectors.append(matchExactRevision(modeArg))
    elif mode == 'closest-revision':
        selectors.append(matchClosestRevision(modeArg))
    elif mode == 'date':
        selectors.append(matchDate(modeArg, 'date'))
    elif mode == 'checkout-date':
        selectors.append(matchDate(modeArg, 'checkout-date'))
    else:
        app.logger.error("unknown mode {0}".format(mode))
        return None

    matcher = allPass(selectors)

    matchingRecordIndex = -1
    for i, r in enumerate(osRecords):
        if matcher(r):
            matchingRecordIndex = i
            break

    if matchingRecordIndex == -1:
        matchingRecord = None
    else:
        if offset < 0:
            # an offset < 0 looks backward in time, or forward in the list
            g = groupby(osRecords[matchingRecordIndex:], key=lambda r: int(r['revision']))
            try:
                o = next(islice(g, -offset, -offset + 1))
                matchingRecord = list(o[1])[0]
            except StopIteration:  # no match or stepped off the end of the list
                matchingRecord = None
        elif offset > 0:
            # look forward in time for the latest build of a particular rev, so
            # flip list
            g = groupby(osRecords[matchingRecordIndex:0:-1], key=lambda r: int(r['revision']))
            try:
                o = next(islice(g, offset, offset + 1))
                matchingRecord = list(o[1])[-1]
            except StopIteration:  # no match of stepped off the end of the list
                matchingRecord = None
        else:
            matchingRecord = osRecords[matchingRecordIndex]
    return matchingRecord


# database handling methods
def openDb():
    dbfile = os.path.join(app.root_path, app.config['MIDAS_DB_FILENAME'])
    if not os.path.isfile(dbfile):
        app.logger.error('database file %s does not exist', dbfile)
        raise IOError(2, 'No such file or directory', dbfile)

    rv = sqlite3.connect(dbfile)
    rv.row_factory = sqlite3.Row
    return rv


def getRecordsFromDb():
    try:
        records = flask.current_app.config["_MIDAS_RECORDS"]
    except KeyError:
        records = None

    db = getDb()
    cursor = db.cursor()

    # get record count
    cursor.execute('select count(1) from _')
    count = int(cursor.fetchone()[0])

    # load db if needed or count has changed
    if records is None or count != len(records):
        cursor.execute('select record from _ order by revision desc,build_date desc')
        records = [json.loads(r[0]) for r in cursor.fetchall()]
        flask.current_app.config["_MIDAS_RECORDS"] = records
    db.close()

    return records


def getDb():
    db = openDb()
    return db


@app.teardown_appcontext
def closeDb(error):
    pass


if __name__ == '__main__':
    app.run()
