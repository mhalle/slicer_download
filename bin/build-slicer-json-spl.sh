#!/bin/sh

SCRIPT_ROOT=$(dirname $0)
SCRIPT="${SCRIPT_ROOT}/../apps/build-slicer-json/build-slicer-json.sh"
DBNAME=/var/cache/slicer-download/download-stats.db
JSONNAME=/var/cache/slicer-download/slicer-download-data.json

exec $SCRIPT $DBNAME $JSONNAME
