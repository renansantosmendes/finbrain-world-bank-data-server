"""Vercel entrypoint: exposes the FastAPI application to the Python runtime."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from world_bank_api.main import app
