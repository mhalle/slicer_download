#!/bin/bash

set -e

script_dir=$(cd $(dirname $0) || exit 1; pwd)

ROOT_DIR=$(realpath "${script_dir}/..")
VIRTUALENV_DIR=$(realpath -m "${ROOT_DIR}/env")
PYTHON_EXECUTABLE=${VIRTUALENV_DIR}/bin/python

APP=slicer_download

DBFILE="${ROOT_DIR}/var/download-stats.sqlite"
GEOIPFILE="${ROOT_DIR}/etc/geoip/db/GeoLite2-City.mmdb"
STATSDATAFILE="${ROOT_DIR}/var/slicer-download-data.json"

APACHELOGS="${ROOT_DIR}/../logs/sites/${APP}/access*"
# EXTRALOGS="${ROOT_DIR}/legacy-logs/*"
EXTRALOGS=""

# Display summary
echo
echo "[slicer_getbuildinfo] Using this config"
echo "  APACHELOGS     : ${APACHELOGS}"
echo "  DBFILE         : ${DBFILE}"
echo "  STATSDATAFILE  : ${STATSDATAFILE}"
echo "  GEOIPFILE      : ${GEOIPFILE}"
echo
echo "[slicer_getbuildinfo] Using these directories"
echo "  ROOT_DIR       : ${ROOT_DIR}"

echo
exec "${PYTHON_EXECUTABLE}" "${ROOT_DIR}/etc/slicer_parselogs" \
    --db ${DBFILE} \
    --geoip ${GEOIPFILE} \
    --statsdata ${STATSDATAFILE} \
    ${APACHELOGS} ${EXTRALOGS}
