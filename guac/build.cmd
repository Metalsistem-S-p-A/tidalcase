docker build -t tidalcase-guac:1.0 .
docker tag tidalcase-guac:1.0 srv-metal53.metalsistem.com:5001/tidalcase-guac:1.0
docker push srv-metal53.metalsistem.com:5001/tidalcase-guac:1.0
::docker builder prune -f
