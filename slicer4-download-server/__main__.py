import flask
from flask import json

import sys
import re
from itertools import groupby, islice
import urllib2
import os
import sqlite3

SupportedOSChoices = ('macosx', 'win', 'linux')
StabilityChoices = ('release', 'nightly', 'any')
ModeChoices = ('revision', 'closest-revision', 'version', 'checkout-date', 'date')

DownloadURLBase = 'http://slicer.kitware.com/midas3/download'
LocalBitstreamPath = '/bitstream'

def main(midasRecordFilename):
    app = flask.Flask(__name__)
    app.config.from_object('config')
    midasRecordCache = MidasRecordCache(midasRecordFilename)

    app.config['MIDAS_RECORD_CACHE'] = midasRecordCache

    app.add_url_rule('/download', view_func=redirectToLocalBitstream)
    app.add_url_rule('/findall', view_func=recordFindAllRequest)
    app.add_url_rule('/find', view_func=recordFindRequest)
    app.add_url_rule('/bitstream/<bitstreamId>', view_func=redirectToSourceBitstream)
    app.add_url_rule('/', view_func=downloadPage)
    app.run()

class MidasRecordCache(object):
    def __init__(self, filename):
        self.filename = filename
        self.mtime = None
        self.data = None
        self.update()

    def update(self):
        try:
            stat = os.stat(self.filename)
        except OSError:
            # could be temporary lack of file
            self.mtime = None

        if self.mtime == stat.st_mtime:
            return

        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute('select record from _ order by revision desc,build_date desc');
            self.data = [json.loads(r[0]) for r in cursor.fetchall()]

        self.mtime = stat.st_mtime
        return self.data

    def get(self):
        self.update()
        return self.data

def downloadPage():
    allRecords, error_message, error_code = recordsMatchingAllOSAndStability()

    return flask.render_template('download.html', R=allRecords)


def getLocalBitstreamURL(r):
    bitstreamId = r['bitstreams'][0]['bitstream_id']

    downloadURL = '{}/{}'.format(LocalBitstreamPath, bitstreamId)
    return downloadURL

def redirectToSourceBitstream(bitstreamId):
    midasBitstreamURL = '{}?bitstream={}'.format(DownloadURLBase, bitstreamId)
    return flask.redirect(midasBitstreamURL)

def cleanupMidasRecord(r):
    if not r: return None
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

def redirectToLocalBitstream():
    record, error_message, error_code = recordMatching()

    if record:
        return flask.redirect(record['download_url'])

    if error_code in (400, 404):
        return (flask.render_template('{}.html'.format(error_code), error_message=error_message), error_code)

    flask.abort(error_code)

def recordFindRequest():
    record, error_message, error_code = recordMatching()

    if record:
        return json.dumps(record)

    if error_code in (400, 404):
        return (flask.render_template('{}.html'.format(error_code), error_message=error_message), error_code)

    flask.abort(error_code)

def recordFindAllRequest():
    allRecords, error_message, error_code = recordsMatchingAllOSAndStability()

    if allRecords:
        return json.dumps(allRecords)

    if error_code in (400, 404):
        return (flask.render_template('{}.html'.format(error_code), error_message=error_message), error_code)

    flask.abort(error_code)

def recordMatching():
    request = flask.request
    app = flask.current_app
    logger = app.logger
    revisionRecords = app.config['MIDAS_RECORD_CACHE'].get()

    os = request.args.get('os') # may generate BadRequest if not present
    if os not in SupportedOSChoices:
        return (None,
            'unknown os "{}": should be one of {}'.format(os, SupportedOSChoices),
            400)

    offset = int(request.args.get('offset', '0'))

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value != None:
            modeDict[name] = value

    if len(modeDict.keys()) == 0:
        modeName = 'date'
        value = '9999-12-31'  # distant date to force last record
    elif len(modeDict.keys()) == 1:
        modeName, value = modeDict.items()[0]
    else:
        return (None,
            "invalid or ambiguous mode: should be one of {}".format(ModeChoices),
            400)

    defaultStability = 'any' if modeName == 'revision' else 'release'
    stability = request.args.get('stability', defaultStability)

    if stability not in StabilityChoices:
        return (None,
                "bad stability {}: should be one of {}".format(stability, StabilityChoices),
                400)

    r = getBestMatching(revisionRecords, os, stability, modeName, value, offset)
    c = cleanupMidasRecord(r)

    if not c:
        return (None,
            "no matching revision for given parameters",
            404)
    return (c, None, 200)

def recordsMatchingAllOSAndStability():
    request = flask.request
    app = flask.current_app
    logger = app.logger
    revisionRecords = app.config['MIDAS_RECORD_CACHE'].get()

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value != None:
            modeDict[name] = value


    offset = int(request.args.get('offset', '0'))

    modeDict = {}
    for name in ModeChoices:
        value = request.args.get(name, None)
        if value != None:
            modeDict[name] = value

    if len(modeDict.keys()) == 0:
        modeName = 'date'
        value = '9999-12-31'  # distant date to force last record
    elif len(modeDict.keys()) == 1:
        modeName, value = modeDict.items()[0]
    else:
        return (None,
            "invalid or ambiguous mode: should be one of {}".format(ModeChoices),
            400)

    results = {}
    for os in SupportedOSChoices:
        osResult = {}
        for stability in ('release', 'nightly'):
            r = getBestMatching(revisionRecords, os, stability, modeName, value, offset)
            osResult[stability] = cleanupMidasRecord(r)
        results[os] = osResult

    return (results, None, 200)

InfoURLMethod='midas.slicerpackages.get.packages'
InfoURLBase='http://slicer.kitware.com/midas3/api/json'

def getMidasRecordsFromURL():
    infoURL = '{}?method={}'.format(InfoURLBase, InfoURLMethod)
    info = None
    try:
        fp = urllib2.urlopen(infoURL)
        info = fp.read()
    finally:
        fp.close()

    return json.loads(info)['data']


def getMidasRecords(filename):
    with open(filename) as fp:
        return json.load(fp)['data']

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
        justDateString = dateString.split(' ')[0] #drop time
        return dt >= justDateString

    return match

def matchVersion(version):
    def match(r):
        rv = getVersion(r)
        if not rv: return False
        rvs = rv.split('.')
        vs = version.split('.')
        for i in range(0, len(vs)):
            if rvs[i] != vs[i]:
                return False
        return True
    return match

VersionRE = re.compile(r'^[A-z]+-([-\d.a-z]+)-20\d\d')

def getVersion(record):
    if record['release']: return record['release']
    m = VersionRE.match(record['name'])
    if not m: return None
    return m.group(1)

def matchStability(s):
    if s == 'nightly':
        return lambda r: r['submissiontype'] == 'nightly'
    if s =='release':
        return lambda r: r['release'] != ""

    return lambda r: True

def getBitstreamInfo(r):
    return r['bitstreams'][0]

def allPass(predlist):
    def pred(x):
        for p in predlist:
            if not p(x): return False
        return True
    return pred


def getBestMatching(revisionRecords, os, stability, mode, modeArg, offset):
    osRecords = filter(matchOS(os), revisionRecords)

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
        app.logger.error("unknown mode {}".format(mode))
        return None

    matcher = allPass(selectors)

    matchingRecordIndex = -1
    for  i, r in enumerate(osRecords):
        if matcher(r):
            matchingRecordIndex = i
            break

    if matchingRecordIndex  == -1:
        matchingRecord = None
    else:
        if offset < 0:
            #an offset < 0 looks backward in time, or forward in the list
            g = groupby(osRecords[matchingRecordIndex:], key=lambda r: int(r['revision']))
            try:
                o = islice(g, -offset, -offset+1).next()
                matchingRecord =  list(o[1])[0]
            except StopIteration: # no match or stepped off the end of the list
                    matchingRecord = None
        elif offset > 0:
            #look forward in time for the latest build of a particular rev, so flip list
            g = groupby(osRecords[matchingRecordIndex:0:-1], key=lambda r: int(r['revision']))
            try:
                o = islice(g, offset, offset+1).next()
                matchingRecord =  list(o[1])[-1]
            except StopIteration: # no match of stepped off the end of the list
                matchingRecord = None
        else:
            matchingRecord = osRecords[matchingRecordIndex]
    return matchingRecord


if __name__ == '__main__':
    main(sys.argv[1])




# class ZZ(object):
#     def __init__(self, d=None):
#         self.a = {}
#         if d:
#             self.update(d)

#     def update(self, d):
#         for k in d.iterkeys():
#             try:
#                 valueset = self.a[k]
#             except KeyError:
#                 valueset = self.a[k] = set()
#             try:
#                 valueset.add(d[k])
#             except TypeError:
#                 pass # ignore unhashable types for lists

#     def get_counts(self):
#         return {k: len(self.a[k]) for k in self.a.iterkeys()}

#     def get(self, k):
#         return self.a[k]
