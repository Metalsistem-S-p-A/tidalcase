# Troubleshooting

Common problems and how to diagnose them. If something's missing here,
open an issue.

## Looking at logs

Everything is dockerised, so logs go through `docker compose logs`. The
services you'll look at most:

```bash
# Manager
docker compose logs -f tidalcase-backend
docker compose logs -f tidalcase-celery-worker
docker compose logs -f tidalcase-celery-beat
docker compose logs -f tidalcase-traefik
docker compose logs -f tidalcase-frontend

# Agent (on the agent host)
docker compose --profile agent logs -f tidalcase-agent
docker compose --profile agent logs -f tidalcase-agent-nginx
docker compose --profile agent logs -f tidalcase-agent-celery-worker
```

The application-level audit log is in the UI under **Admin → Logs**.

## Stack won't come up

```bash
docker compose ps
docker compose logs --tail=200
```

Look for the first traceback. Common causes:

- **Port already in use.** Something else is on 80, 443, 9443 or 5443.
  `ss -tlnp | grep -E ':80|:443|:9443|:5443'` and stop the offender, or
  remap the ports in `docker-compose.yml`.
- **`.env` not picked up.** Make sure it lives next to `docker-compose.yml`,
  not in a subdirectory. `docker compose config` prints the resolved
  configuration — variables you forgot to set show up as empty.
- **Migrations failing.** Backend logs will show the Alembic error. For a
  development DB you can usually wipe it with `docker compose down -v` and
  start over (**this deletes all data**).

## Can't open the UI

If `https://<DOMAIN>` doesn't respond:

1. Is Traefik routing? `docker compose logs tidalcase-traefik | grep -i
   error`. A missing TLS cert is a typical cause.
2. Is the frontend healthy? `docker compose ps tidalcase-frontend`.
3. Is `DOMAIN` actually pointing at this host? `dig +short <DOMAIN>` from
   somewhere outside.
4. Is something blocking 443 in your firewall?
5. Visit `http://<DOMAIN>` — Traefik should 301 you to HTTPS. If it
   doesn't, Traefik isn't seeing the frontend's labels.

## Can't log in

- **Wrong password but you don't remember setting one** — for a fresh
  install the password is in `backend/credentials.txt`:

  ```bash
  docker compose exec tidalcase-backend cat /app/data/credentials.txt
  ```

- **JWT errors / "session expired immediately"** — usually a sign
  `SECRET_KEY` changed between restarts. Set it explicitly in `.env` so it
  doesn't get regenerated.

- **OIDC redirect loop** — the redirect URI registered on the IdP must
  match `https://<DOMAIN>/api/auth/oidc/callback` **exactly**. Mismatched
  scheme or trailing slash will silently bounce you.

- **LDAP "invalid credentials" with correct password** — turn on the
  provider's debug flag from **Admin → Auth providers → <provider> → Debug**;
  the backend log will then show the exact bind error.

## Forgotten admin password

```bash
docker compose exec tidalcase-backend python -c '
from app import create_app, db
from app.models.user import User
from app.utils.extensions import bcrypt
app = create_app()
with app.app_context():
    u = User.query.filter_by(username="admin").one()
    u.password = bcrypt.generate_password_hash("CHANGEME").decode()
    db.session.commit()
    print("admin password reset")
'
```

Log in with `CHANGEME` and rotate immediately.

## Session won't launch

When a user clicks **Launch** and nothing happens, or it errors out:

1. **Admin → Logs** — look for a `tide.launch.failed` entry with a reason.
2. Is any agent online? **Admin → Agents** should show at least one
   **Online** with free capacity.
3. Image pull failures — check the chosen agent's logs:

   ```bash
   docker compose --profile agent logs -f tidalcase-agent-celery-worker
   ```

   Common: the agent host can't reach the registry, or the registry
   credentials in **Admin → Registries** are wrong.
4. Out-of-capacity — every online agent is full. Lower the tide's resource
   limits, or add another agent.

## Tide opens but VNC stays black

The WebSocket from the browser goes **directly to the agent's nginx** on
port 7443 — not through the manager. Check:

- Can the user's browser reach `https://<agent-host>:7443`? Try opening
  that URL directly in a new tab — you should get an nginx response (often
  a 404 since you didn't hit a session path), not a connection refused.
- TLS cert on the agent — modern browsers refuse WebSockets to self-signed
  certs unless the user has accepted them at least once over plain HTTPS.
- Agent nginx logs:

  ```bash
  docker compose --profile agent logs -f tidalcase-agent-nginx
  ```

## Agent shows as Offline

- Did `TIDALCASE_MANAGER_URL` point at the manager **as seen from the agent
  host** (not from your laptop)? Run `curl -k $TIDALCASE_MANAGER_URL/api/health`
  from inside the agent container.
- Is Redis reachable from the agent? `docker compose --profile agent exec
  tidalcase-agent redis-cli -h tidalcase-redis ping` should return `PONG`.
  If the agent is on a different host, the bundled Redis won't be
  reachable — see [agents.md](agents.md).
- Was the join token valid? The backend logs reject expired or unknown
  tokens explicitly.

## Registry pull errors

- The bundled registry listens on the `registry` Traefik entrypoint (port
  5443) — make sure that port is reachable from your agent hosts.
- Self-signed cert? Docker daemon needs the CA in `/etc/docker/certs.d/<host>:<port>/ca.crt`
  on each agent host, or you have to mark the registry as insecure in
  `/etc/docker/daemon.json` (not recommended).
- Auth — Tidalcase pushes registry credentials to agents on heartbeat. If
  you rotated them, give it a heartbeat cycle (~30 s) or click **Refresh
  credentials** on the agent.

## Reset everything

When you genuinely want to start over (this **deletes all data**):

```bash
docker compose down -v
# remove host-mounted state too, if any:
sudo rm -rf /etc/tidalcase/configs
docker compose up -d
```

You'll get a fresh `admin` user and a new credentials.txt on next start.

## Diagnostic bundle

Helpful when reporting an issue:

```bash
docker compose ps                            > tidalcase-debug.txt
docker compose logs --tail=500              >> tidalcase-debug.txt
docker compose config                       >> tidalcase-debug.txt
docker version                              >> tidalcase-debug.txt
```

Scrub `SECRET_KEY`, `TIDALCASE_JOIN_TOKEN`, DB passwords and any Authentik
secrets before sharing it.
