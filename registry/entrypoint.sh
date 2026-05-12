#!/bin/sh
registry serve /etc/docker/registry/config.yml &
exec python3 /catalog_server.py
