# Deployment

This guide walks through deploying the Tidalcase **manager** on a Linux host
and getting it ready for real users. For agents (the hosts that actually run
tide sessions), see [`agents.md`](agents.md).

## Sizing

The manager itself is light: a single VM with **2 vCPU / 4 GB RAM / 20 GB
disk** is enough to drive dozens of concurrent tide sessions, as long as the
sessions themselves run on separate agent hosts. Memory grows mostly with
Celery worker concurrency and the size of the audit log.

Tide sessions are heavy, and they run on agents — size those according to
what you put inside (a Firefox tide is small; a JetBrains IDE tide is not).

## Prerequisites

- Linux host with Docker Engine 24+ and Docker Compose v2.
- DNS record pointing at the manager host (`tidalcase.example.com`).
- Inbound 80/443 open from your users.
- A TLS certificate. Tidalcase delegates HTTPS to Traefik, which reads certs
  from `/etc/tidalcase/certs/` via its file provider. Use a wildcard, a
  Let's Encrypt cert renewed externally, or self-signed for testing.

## Services in `docker-compose.yml`

Running `docker compose up -d` (no profiles) brings up the manager stack:

| Service                    | Role                                                       |
| -------------------------- | ---------------------------------------------------------- |
| `tidalcase-traefik`        | Reverse proxy, terminates TLS, exposes 80/443/9443/5443    |
| `tidalcase-frontend`       | Angular app served by nginx                                |
| `tidalcase-backend`        | Flask API on gunicorn, holds the source of truth           |
| `tidalcase-celery-worker`  | Async jobs (image pulls, prunes, agent monitoring)         |
| `tidalcase-celery-beat`    | Periodic scheduler (health checks, expirations)            |
| `tidalcase-redis`          | Celery broker + result backend, session cache              |

Optional profiles:

| Profile     | Adds                                                       |
| ----------- | ---------------------------------------------------------- |
| `db`        | `tidalcase-postgres` for production-grade storage          |
| `auth`      | `tidalcase-authentik` + `tidalcase-authentik-worker` SSO   |
| `registry`  | `tidalcase-registry` (a Docker registry with an icon UI)   |
| `agent`     | The agent stack — see [`agents.md`](agents.md)             |

## Volumes

| Volume                   | What's in it                                       |
| ------------------------ | -------------------------------------------------- |
| `tidalcase-data`         | Backend data: SQLite DB, secret key, join tokens, credentials.txt |
| `tidalcase-redis`        | Redis persistence (AOF/RDB)                        |
| `tidalcase-postgres`     | PostgreSQL data dir (only with `--profile db`)     |
| `registry_data`          | Docker registry blobs (only with `--profile registry`) |
| `agent-data`             | Per-agent state (only on agent hosts)              |
| `vnc-nginx-instances`    | nginx per-session vhost configs (only on agents)   |

Back up `tidalcase-data` and (if used) `tidalcase-postgres` regularly. Losing
them means losing users, tides, agents, audit logs.

## TLS

Traefik reads its dynamic configuration and certificates from the host
directory **`/etc/tidalcase/certs/`**, mounted read-only at `/certs`:

```yaml
volumes:
  - /etc/tidalcase/certs:/certs:ro
```

Provide a Traefik dynamic config file there that points to your cert(s). A
minimal `/etc/tidalcase/certs/dynamic.yml`:

```yaml
tls:
  certificates:
    - certFile: /certs/fullchain.pem
      keyFile:  /certs/privkey.pem
```

For automatic Let's Encrypt issuance you can either:

- Use a wildcard cert renewed by an external tool (acme.sh, certbot) and let
  Tidalcase just consume it via the file provider; **or**
- Enable Traefik's built-in ACME resolver by editing the `command:` block of
  `tidalcase-traefik` in `docker-compose.yml` to add a `certificatesresolvers`
  section and an `entrypoints.websecure.http.tls.certresolver=...` flag.

## First start

On the very first start the backend will:

1. Generate `backend/data/secret_key` (used by Flask).
2. Run all Alembic migrations against `DATABASE_URL`.
3. Create a default `admin` user.
4. Write the admin password to `backend/data/credentials.txt`.
5. Generate a `backend/data/join_token` used to register agents.

Retrieve the admin password:

```bash
docker compose exec tidalcase-backend cat /app/data/credentials.txt
```

Log in at `https://<DOMAIN>`, change the password under
**Profile → Change password**, and remove the credentials file from the
volume:

```bash
docker compose exec tidalcase-backend rm /app/data/credentials.txt
```

## Switching to PostgreSQL

For anything beyond a single-user evaluation, move off SQLite:

1. In `.env`, set:

   ```env
   DATABASE_URL=postgresql+psycopg2://tidalcase:<password>@tidalcase-postgres:5432/tidalcase
   POSTGRES_DB=tidalcase
   POSTGRES_USER=tidalcase
   POSTGRES_PASSWORD=<password>
   ```

2. Bring the stack up with the `db` profile:

   ```bash
   docker compose --profile db up -d
   ```

3. The backend runs migrations against Postgres on boot.

Going from a populated SQLite DB to Postgres requires a manual dump/restore;
there is no built-in migration tool yet.

## Backups

A minimal backup script:

```bash
#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d-%H%M%S)
DEST=/srv/backups/tidalcase

mkdir -p "$DEST"

# Backend data (SQLite + secrets + uploads)
docker run --rm -v tidalcase-data:/data -v "$DEST":/out alpine \
  tar czf "/out/data-$STAMP.tgz" -C /data .

# Postgres dump if you use it
if docker compose ps tidalcase-postgres >/dev/null 2>&1; then
  docker compose exec -T tidalcase-postgres \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
    | gzip > "$DEST/pg-$STAMP.sql.gz"
fi
```

Schedule it from cron or systemd. Test the restore path before you need it.

## Hardening checklist

- [ ] `SECRET_KEY` is long and random; never reuse a sample value.
- [ ] `.env` permissions are `600` and the file is not in Git.
- [ ] DB password isn't the default; rotate the bundled Postgres password.
- [ ] Authentication is configured beyond the default `admin` account
      (see [`auth-providers.md`](auth-providers.md)).
- [ ] MFA is enabled for admins.
- [ ] Audit log retention is set in **Admin → Settings**.
- [ ] Firewall blocks 9443/5443 from the public internet unless you actually
      expose Authentik or the bundled registry externally.
- [ ] The Docker socket on agent hosts is mounted only into the agent
      services — never expose it remotely.
- [ ] Backups run and have been test-restored.

## Reverse-proxying behind another proxy

If Tidalcase sits behind another reverse proxy (cloud LB, your existing
nginx, etc.) you can either:

- Let Traefik keep terminating TLS and just forward TCP/443 to it; or
- Disable TLS on Traefik (drop the `tls=true` labels on the
  `tidalcase-frontend` router) and let the upstream proxy handle TLS.

The WebSocket connection from the browser to the **agent's** nginx on port
7443 must remain end-to-end — that traffic doesn't go through the manager.
