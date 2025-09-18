import sys
import os

# Ruta donde subiste api_server.py
path = '/home/flowshop2kee/mysite'
if path not in sys.path:
    sys.path.append(path)

from api_server import app as application