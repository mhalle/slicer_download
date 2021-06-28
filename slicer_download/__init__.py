import json
import os
import requests
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from enum import Enum


class ServerAPI(Enum):
    Midas_v1 = 1
    Girder_v1 = 2


def getServerAPI():
    return ServerAPI[os.getenv("SLICER_DOWNLOAD_SERVER_API", ServerAPI.Midas_v1.name)]


def getServerAPIUrl():
    return {
        ServerAPI.Midas_v1: "http://slicer.kitware.com/midas3/api/json",
        ServerAPI.Girder_v1: "https://slicer-packages.kitware.com/api/v1",
    }[getServerAPI()]


def getMidasRecordsFromURL():
    InfoURLMethod = 'midas.slicerpackages.get.packages'

    infoURL = '{0}?productname=Slicer&method={1}'.format(getServerAPIUrl(), InfoURLMethod)

    fp = urllib.request.urlopen(infoURL)
    info = fp.read()
    fp.close()

    return json.loads(info)['data']


def getGirderRecordsFromURL():
    result = requests.get("{0}/app/5f4474d0e1d8c75dfc705482/package?limit=0".format(getServerAPIUrl()))
    return result.json()


def getRecordsFromURL():
    return {
        ServerAPI.Midas_v1: getMidasRecordsFromURL,
        ServerAPI.Girder_v1: getGirderRecordsFromURL,
    }[getServerAPI()]()


def openDb(database_filepath):
    """Return opened database connection."""
    database_connection = sqlite3.connect(database_filepath)
    database_connection.row_factory = sqlite3.Row
    return database_connection
