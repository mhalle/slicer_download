#!/bin/sh

APP=slicer_download
ROOT=${HOME}/apps/${APP}
PYTHON="${ROOT}/env/bin/python"

DBFILE="${ROOT}/var/download-stats.sqlite"
GEOIPFILE="${ROOT}/etc/geoip/db/GeoLite2-City.mmdb"
STATSDATAFILE="${ROOT}/var/slicer-download-data.json"

APACHELOGS="${HOME}/logs/sites/${APP}/access*"
# EXTRALOGS="${ROOT}/legacy-logs/*"
EXTRALOGS=""

MODULE="${ROOT}/slicer4-download"

exec "${PYTHON}" "${ROOT}/etc/slicer_parselogs" \
    --db ${DBFILE} \
    --geoip ${GEOIPFILE} \
    --statsdata ${STATSDATAFILE} \
    ${APACHELOGS} ${EXTRALOGS}
