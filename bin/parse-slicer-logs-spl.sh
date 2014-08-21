#!/bin/sh

SCRIPT_ROOT=$(dirname $0)
SCRIPT="${SCRIPT_ROOT}/../apps/parse-slicer-logs/parse-slicer-logs.sh"
DBNAME=/var/cache/slicer-download/download-stats.db
LOGS="/var/log/httpd/slicer-download-access_log*"

exec "$SCRIPT" "$DBNAME" $LOGS
