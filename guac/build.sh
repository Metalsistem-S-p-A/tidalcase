#!/bin/bash
docker build -t kasm-desktop-metalsistem:1.0 .
docker tag kasm-desktop-metalsistem:1.0 srv-metal53.metalsistem.com:5001/kasm-desktop-metalsistem:1.0
docker push srv-metal53.metalsistem.com:5001/kasm-desktop-metalsistem:1.0
docker builder prune -f
