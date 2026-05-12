#!/bin/sh
/opt/guacamole/sbin/guacd -f -b 0.0.0.0 -L info &
exec node /app/server.js "$GUAC_KEY"