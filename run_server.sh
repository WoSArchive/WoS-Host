#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting Gunicorn..."
gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --log-level info
