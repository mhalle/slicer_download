#!/bin/sh

SCRIPT_ROOT=$(dirname $0)
PYSCRIPT="${SCRIPT_ROOT}/../apps/parse-slicer-logs"
DBNAME=/var/cache/slicer-download/download-stats.db
LOGS="/var/log/httpd/slicer-download-access_log*"

exec python2.6 $PYSCRIPT "$DBNAME" $LOGS
