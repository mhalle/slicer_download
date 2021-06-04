import os

DEBUG = True
DB_FILE = os.environ.get("SLICER_DOWNLOAD_DB_FILE", "../etc/fallback/slicer-midas-records.sqlite")
