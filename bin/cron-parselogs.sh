#!/bin/bash

set -e

script_dir=$(cd $(dirname $0) || exit 1; pwd)

ROOT_DIR=$(realpath "${script_dir}/..")
VIRTUALENV_DIR=$(realpath -m "${ROOT_DIR}/env")
PYTHON_EXECUTABLE=${VIRTUALENV_DIR}/bin/python


SLICER_DOWNLOAD_STATS_DB_FILE="${ROOT_DIR}/var/download-stats.sqlite"
SLICER_DOWNLOAD_STATS_DATA_FILE="${ROOT_DIR}/var/slicer-download-data.json"

GEOIP_DB_DIR=${ROOT_DIR}/etc/geoip/db
GEOIP_DB_FILE="${GEOIP_DB_DIR}/GeoLite2-City.mmdb"

SLICER_DOWNLOAD_ACCESS_LOGS="${ROOT_DIR}/../logs/sites/download_slicer_org/access*"
# EXTRALOGS="${ROOT_DIR}/legacy-logs/*"
EXTRALOGS=""

# Display summary
echo
echo "[slicer_parselogs] Using this config"
echo "  SLICER_DOWNLOAD_ACCESS_LOGS      : ${SLICER_DOWNLOAD_ACCESS_LOGS}"
echo "  SLICER_DOWNLOAD_STATS_DB_FILE    : ${SLICER_DOWNLOAD_STATS_DB_FILE}"
echo "  SLICER_DOWNLOAD_STATS_DATA_FILE  : ${SLICER_DOWNLOAD_STATS_DATA_FILE}"
echo "  GEOIP_DB_FILE                    : ${GEOIP_DB_FILE}"
echo
echo "[slicer_parselogs] Using these directories"
echo "  ROOT_DIR       : ${ROOT_DIR}"

echo
export PYTHONPATH=${ROOT_DIR}/etc/
exec "${PYTHON_EXECUTABLE}" "${ROOT_DIR}/etc/slicer_parselogs" \
    --db ${SLICER_DOWNLOAD_STATS_DB_FILE} \
    --geoip ${GEOIP_DB_FILE} \
    --statsdata ${SLICER_DOWNLOAD_STATS_DATA_FILE} \
    ${SLICER_DOWNLOAD_ACCESS_LOGS} \
    ${EXTRALOGS}
