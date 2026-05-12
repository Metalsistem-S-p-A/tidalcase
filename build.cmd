docker build -t tidalcase-backend:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Backend" ^
  --label "org.opencontainers.image.description=Tidalcase backend service" ^
  --label "tidalcase.categories=Tidalcase,Infrastructure" ^
  --label "tidalcase.icon=favicon.png" ^
  ./backend
docker build -t tidalcase-frontend:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Frontend" ^
  --label "org.opencontainers.image.description=Tidalcase web frontend" ^
  --label "tidalcase.categories=Tidalcase,Infrastructure" ^
  --label "tidalcase.icon=favicon.png" ^
  ./frontend
docker build -t tidalcase-agent:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Agent" ^
  --label "org.opencontainers.image.description=KasmVNC remote desktop agent" ^
  --label "tidalcase.categories=Tidalcase" ^
  --label "tidalcase.icon=favicon.png" ^
  ./agent
docker build -t tidalcase-agent-nginx:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Agent Nginx" ^
  --label "org.opencontainers.image.description=Tidalcase agent reverse proxy" ^
  --label "tidalcase.categories=Tidalcase,Infrastructure" ^
  --label "tidalcase.icon=favicon.png" ^
  -f ./agent/nginx.Dockerfile ./agent
docker build -t tidalcase-guac:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Guac" ^
  --label "org.opencontainers.image.description=RDP/VNC/SSH session via Guacamole" ^
  --label "tidalcase.categories=Tidalcase" ^
  --label "tidalcase.icon=favicon.png" ^
  ./guac
docker build -t tidalcase-registry:1.0 ^
  --label "org.opencontainers.image.title=Tidalcase Registry" ^
  --label "org.opencontainers.image.description=Tidalcase image registry" ^
  --label "tidalcase.categories=Tidalcase,Infrastructure" ^
  --label "tidalcase.icon=favicon.png" ^
  ./registry

docker tag tidalcase-backend:1.0 tidalcase.metalsistem.com:5443/tidalcase-backend:1.0
docker tag tidalcase-frontend:1.0 tidalcase.metalsistem.com:5443/tidalcase-frontend:1.0
docker tag tidalcase-agent:1.0 tidalcase.metalsistem.com:5443/tidalcase-agent:1.0
docker tag tidalcase-agent-nginx:1.0 tidalcase.metalsistem.com:5443/tidalcase-agent-nginx:1.0
docker tag tidalcase-guac:1.0 tidalcase.metalsistem.com:5443/tidalcase-guac:1.0
docker tag tidalcase-registry:1.0 tidalcase.metalsistem.com:5443/tidalcase-registry:1.0

docker tag tidalcase-backend:1.0 tidalcase.metalsistem.com:5443/tidalcase-backend:latest
docker tag tidalcase-frontend:1.0 tidalcase.metalsistem.com:5443/tidalcase-frontend:latest
docker tag tidalcase-agent:1.0 tidalcase.metalsistem.com:5443/tidalcase-agent:latest
docker tag tidalcase-agent-nginx:1.0 tidalcase.metalsistem.com:5443/tidalcase-agent-nginx:latest
docker tag tidalcase-guac:1.0 tidalcase.metalsistem.com:5443/tidalcase-guac:latest
docker tag tidalcase-registry:1.0 tidalcase.metalsistem.com:5443/tidalcase-registry:latest

docker push tidalcase.metalsistem.com:5443/tidalcase-backend:1.0
docker push tidalcase.metalsistem.com:5443/tidalcase-frontend:1.0
docker push tidalcase.metalsistem.com:5443/tidalcase-agent:1.0
docker push tidalcase.metalsistem.com:5443/tidalcase-agent-nginx:1.0
docker push tidalcase.metalsistem.com:5443/tidalcase-guac:1.0
docker push tidalcase.metalsistem.com:5443/tidalcase-registry:1.0

docker push tidalcase.metalsistem.com:5443/tidalcase-backend:latest
docker push tidalcase.metalsistem.com:5443/tidalcase-frontend:latest
docker push tidalcase.metalsistem.com:5443/tidalcase-agent:latest
docker push tidalcase.metalsistem.com:5443/tidalcase-agent-nginx:latest
docker push tidalcase.metalsistem.com:5443/tidalcase-guac:latest
docker push tidalcase.metalsistem.com:5443/tidalcase-registry:latest