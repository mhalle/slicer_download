#!/bin/sh

ROOT="${HOME}/apps/slicer_download"
DBFILE="${ROOT}/var/slicer-midas-records.sqlite"
PYTHON="${ROOT}/env/bin/python"

"${PYTHON}" "${ROOT}/etc/slicer_getbuildinfo" ${DBFILE} \
    && sqlite3 ${DBFILE} 'delete from _ where revision = 5266433;'

