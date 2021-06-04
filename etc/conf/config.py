import os

DEBUG = False
DB_FILE = os.environ.get("SLICER_DOWNLOAD_DB_FILE", "../var/slicer-midas-records.sqlite")
