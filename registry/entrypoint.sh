#!/bin/sh
registry serve /etc/distribution/config.yml &
exec python3 /catalog_server.py
