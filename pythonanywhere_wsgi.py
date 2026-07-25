import os
import sys
from pathlib import Path


# Change this folder name if you upload the project with another name.
PROJECT_DIR = Path.home() / "Carpinteria"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("CARPINTERIA_PASSWORD", "cambia-esta-contrasena")

from app import app as application  # noqa: E402
