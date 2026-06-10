import sys
import os
# Ensure the workspace directory is the FIRST on sys.path so local
# modules (app.py, extensions.py, models.py) shadow any installed packages.
sys.path.insert(0, os.path.dirname(__file__))
