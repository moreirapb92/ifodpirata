"""
WSGI entry point for Render / Gunicorn.
"""
import os
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portal.app import create_app

app = create_app()
