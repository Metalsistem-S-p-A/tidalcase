FROM registry:2

USER root
RUN apk add --no-cache python3 py3-pip tini && \
    pip install requests --break-system-packages

COPY catalog_server.py /catalog_server.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/entrypoint.sh"]
