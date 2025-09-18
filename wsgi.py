#!/usr/bin/env python3.10

import sys
import os

# Agregar el directorio del proyecto al path
project_home = '/home/flowshop2kee/mysite'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Importar la aplicación Flask
from api_server import app as application

if __name__ == "__main__":
    application.run()