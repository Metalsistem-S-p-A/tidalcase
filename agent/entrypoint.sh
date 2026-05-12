#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    if [ "$FLASK_DEBUG" = "1" ]; then
        echo "Starting in Debug Mode..."
        exec python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5678 -m gunicorn --workers 1 --timeout 3600 --bind 0.0.0.0:7272 app:agent_app
    else
        echo "Starting in Production Mode..."
        exec gunicorn --config gunicorn.conf.py app:agent_app
    fi
else
    exec "$@"
fi