FROM guacamole/guacd:latest

USER root
RUN apk add --no-cache nodejs npm tini

WORKDIR /app
RUN npm install guacamole-lite express guacamole-common-js

COPY public public
COPY server.js server.js
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

USER 1000
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/entrypoint.sh"]