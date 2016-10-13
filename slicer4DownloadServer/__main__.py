import sys
import os

from slicer4DownloadServer import app

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

app.run()
