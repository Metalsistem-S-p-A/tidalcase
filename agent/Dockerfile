FROM python:3.12-slim

RUN useradd -m tidalcase

WORKDIR /agent
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /agent/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /agent/
RUN chown -R tidalcase:tidalcase /agent

COPY gunicorn.conf.py /gunicorn.conf.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /nginx-instances && chown -R tidalcase:tidalcase /nginx-instances

EXPOSE 7272

USER tidalcase

ENTRYPOINT ["/entrypoint.sh"]
