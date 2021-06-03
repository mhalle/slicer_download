#!/bin/bash

set -e

script_dir=$(cd $(dirname $0) || exit 1; pwd)

ROOT_DIR=$(realpath "${script_dir}/..")
VIRTUALENV_DIR=$(realpath -m "${ROOT_DIR}/env")
PYTHON_EXECUTABLE=${VIRTUALENV_DIR}/bin/python

DB_FILE="${ROOT_DIR}/var/slicer-midas-records.sqlite"

"${PYTHON_EXECUTABLE}" "${ROOT_DIR}/etc/slicer_getbuildinfo" ${DB_FILE}
