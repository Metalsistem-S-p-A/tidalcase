#!/bin/bash
set -e

# Fix ownership of the data volume (mounted as root at runtime)
mkdir -p /app/data
chown -R tidalcase:tidalcase /app/data

if [ "$SERVICE_TYPE" = "backend" ]; then
    gosu tidalcase python setup_app.py
fi

if [ $# -eq 0 ]; then
    if [ "$FLASK_DEBUG" = "1" ]; then
        echo "Starting in Debug Mode..."
        exec gosu tidalcase python -m debugpy --listen 0.0.0.0:5678 -m gunicorn --workers 1 --timeout 3600 --bind 0.0.0.0:5000 run:tidalcase_app
    else
        echo "Starting in Production Mode..."
        exec gosu tidalcase gunicorn --config gunicorn.conf.py run:tidalcase_app
    fi
else
    exec gosu tidalcase "$@"
fi
