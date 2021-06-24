#!/bin/bash

set -e

script_dir=$(cd $(dirname $0) || exit 1; pwd)

ROOT_DIR=$(realpath "${script_dir}/..")
VIRTUALENV_DIR=$(realpath -m "${ROOT_DIR}/env")
PYTHON_EXECUTABLE=${VIRTUALENV_DIR}/bin/python

# Customizing environment
echo -n "[slicer_getbuildinfo] Looking for ${script_dir}/.start_environment "
if [ -e "${script_dir}/.start_environment" ]; then
  source "${script_dir}/.start_environment"
  echo "[ok]"
else
  echo "[not found]"
fi

export SLICER_DOWNLOAD_SERVER_CONF="${SLICER_DOWNLOAD_SERVER_CONF:-${ROOT_DIR}/etc/conf/config.py}"
export SLICER_DOWNLOAD_SERVER_API=$(PYTHONPATH=${ROOT_DIR} ${PYTHON_EXECUTABLE} -c "import slicer_download_server as sds; print(sds.getServerAPI().name)")
SLICER_DOWNLOAD_DB_FILE=$(PYTHONPATH=${ROOT_DIR} ${PYTHON_EXECUTABLE} -c "import slicer_download_server as sds; print(sds.dbFilePath())")

# Sanity checks
if [ ! -e "${SLICER_DOWNLOAD_SERVER_CONF}" ]; then
  echo "SLICER_DOWNLOAD_SERVER_CONF set to an nonexistent file: ${SLICER_DOWNLOAD_SERVER_CONF}"
  exit 99
fi

# Display summary
echo
echo "[slicer_getbuildinfo] Using this config"
echo "  SLICER_DOWNLOAD_SERVER_CONF: ${SLICER_DOWNLOAD_SERVER_CONF}"
echo "  SLICER_DOWNLOAD_SERVER_API : ${SLICER_DOWNLOAD_SERVER_API}"
echo "  SLICER_DOWNLOAD_DB_FILE    : ${SLICER_DOWNLOAD_DB_FILE}"
echo
echo "[slicer_getbuildinfo] Using these directories"
echo "  ROOT_DIR       : ${ROOT_DIR}"

echo
"${PYTHON_EXECUTABLE}" "${ROOT_DIR}/etc/slicer_getbuildinfo" ${SLICER_DOWNLOAD_DB_FILE}
