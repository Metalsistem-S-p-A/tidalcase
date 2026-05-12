# Configuration

Tidalcase has two layers of configuration:

1. **Environment variables**, read by `docker-compose.yml` and the backend
   at boot. These set up the infrastructure (DB, secret key, hostnames).
2. **Admin panel**, which configures everything Tidalcase itself manages
   (users, tides, agents, auth providers, registries, storage).

Anything that can be reconfigured at runtime lives in the admin panel.
Environment variables are for bootstrapping only.

## Environment variables

All variables live in a single `.env` file at the project root. The full
template is shipped as [`.env.example`](../.env.example).

### Core (always required)

| Variable       | Required | Default                                 | Notes |
| -------------- | -------- | --------------------------------------- | ----- |
| `DOMAIN`       | yes      | —                                       | Public hostname Traefik serves. Used in TLS routing labels. |
| `DATABASE_URL` | yes      | `sqlite:////app/data/tidalcase.db`      | SQLAlchemy URL. SQLite is fine to evaluate; switch to Postgres for production. |
| `SECRET_KEY`   | yes      | —                                       | Signs session cookies and JWTs. Generate with `openssl rand -hex 32`. **Rotating this invalidates all sessions.** |

### Celery / Redis

These are wired in `docker-compose.yml` and rarely need to change:

| Variable                  | Default                              |
| ------------------------- | ------------------------------------ |
| `CELERY_BROKER_URL`       | `redis://tidalcase-redis:6379/0`     |
| `CELERY_RESULT_BACKEND`   | `redis://tidalcase-redis:6379/0`     |

The agent uses DB `1` on the same Redis (`/1`) to keep its queues isolated
from the manager.

### PostgreSQL (only with `--profile db`)

| Variable             | Default      |
| -------------------- | ------------ |
| `POSTGRES_DB`        | `tidalcase`  |
| `POSTGRES_USER`      | `tidalcase`  |
| `POSTGRES_PASSWORD`  | `tidalcase`  |

When `--profile db` is on, set `DATABASE_URL` accordingly:

```env
DATABASE_URL=postgresql+psycopg2://tidalcase:<password>@tidalcase-postgres:5432/tidalcase
```

### Authentik SSO (only with `--profile auth`)

| Variable                  | Notes |
| ------------------------- | ----- |
| `AUTHENTIK_PG_HOST`       | Defaults to `tidalcase-postgres`. |
| `AUTHENTIK_PG_USER`       | Distinct user is recommended. |
| `AUTHENTIK_PG_PASSWORD`   | Required. |
| `AUTHENTIK_PG_DB`         | Defaults to `authentik`. |
| `AUTHENTIK_SECRET_KEY`    | Generate with `openssl rand -base64 60`. |

### Bundled Docker registry (only with `--profile registry`)

| Variable                | Default                 | Notes |
| ----------------------- | ----------------------- | ----- |
| `REGISTRY_NAME`         | `Tidalcase Registry`    | Displayed in the admin UI. |
| `REGISTRY_IMAGE_PREFIX` | empty                   | Optional prefix shown in front of image names. |

### Agent (only with `--profile agent`)

| Variable                 | Notes |
| ------------------------ | ----- |
| `TIDALCASE_JOIN_TOKEN`   | Token issued by the manager UI. Secret. |
| `TIDALCASE_MANAGER_URL`  | URL the agent uses to reach the manager. |
| `TIDALCASE_AGENT_URL`    | URL the manager uses to reach this agent (port 7443). |

See [`agents.md`](agents.md) for how to issue the token.

### Image overrides (optional)

If you mirror Tidalcase images into your own registry, set:

| Variable                      | Default |
| ----------------------------- | ------- |
| `TIDALCASE_BACKEND_IMAGE`     | `ghcr.io/metalsistem-s-p-a/tidalcase-backend:latest` |
| `TIDALCASE_FRONTEND_IMAGE`    | `ghcr.io/metalsistem-s-p-a/tidalcase-frontend:latest` |
| `TIDALCASE_AGENT_IMAGE`       | `ghcr.io/metalsistem-s-p-a/tidalcase-agent:latest` |
| `TIDALCASE_AGENT_NGINX_IMAGE` | `ghcr.io/metalsistem-s-p-a/tidalcase-agent-nginx:latest` |
| `TIDALCASE_REGISTRY_IMAGE`    | `ghcr.io/metalsistem-s-p-a/tidalcase-registry:latest` |

The Celery worker and beat services reuse `TIDALCASE_BACKEND_IMAGE`, so one
override is enough to redirect the whole manager stack.

## Admin panel

After logging in as an admin you'll see a left-hand admin menu with these
sections:

| Section            | What you configure                                          |
| ------------------ | ----------------------------------------------------------- |
| **Users**          | Create/delete users, assign groups, force password reset, enable MFA. |
| **Groups**         | RBAC: a group bundles permissions and tide entitlements. Each user is in one or more groups. |
| **Tides**          | Tide catalog: image, command, env, CPU/memory, exposed ports, persistent volumes, storage mounts, who can launch it. |
| **Agents**         | Registered agent hosts, health status, current load, prune/maintenance actions. |
| **Registries**     | External Docker registries Tidalcase can pull tide images from (credentials stored encrypted). |
| **Auth providers** | LDAP / OIDC / Azure AD providers — see [`auth-providers.md`](auth-providers.md). |
| **Storage**        | rclone-backed storage providers and their mount mappings — see [`storage.md`](storage.md). |
| **Logs**           | Audit log (login attempts, tide launches, admin actions). |
| **Settings**       | Global settings: session timeout, log retention, default group, branding. |

## Building from source

Most users pull the prebuilt images from GHCR. If you want to build locally:

```bash
docker compose build           # builds whichever services have a 'build:' key
# or build a single component:
docker build -t tidalcase-backend:dev   backend
docker build -t tidalcase-frontend:dev  frontend
docker build -t tidalcase-agent:dev     -f agent/Dockerfile        agent
docker build -t tidalcase-agent-nginx:dev -f agent/nginx.Dockerfile agent
docker build -t tidalcase-registry:dev  registry
```

Then point the `*_IMAGE` env vars (or `image:` lines) at your local tags.

### Publishing your own images to GHCR

If you fork Tidalcase and want to host the images on your own GHCR
namespace:

```bash
echo "$CR_PAT" | docker login ghcr.io -u <your-github-user> --password-stdin

for c in backend frontend agent agent-nginx registry; do
  docker tag tidalcase-$c:dev ghcr.io/<your-github-user>/tidalcase-$c:latest
  docker push ghcr.io/<your-github-user>/tidalcase-$c:latest
done
```

Then in `.env`:

```env
TIDALCASE_BACKEND_IMAGE=ghcr.io/<your-github-user>/tidalcase-backend:latest
TIDALCASE_FRONTEND_IMAGE=ghcr.io/<your-github-user>/tidalcase-frontend:latest
TIDALCASE_AGENT_IMAGE=ghcr.io/<your-github-user>/tidalcase-agent:latest
TIDALCASE_AGENT_NGINX_IMAGE=ghcr.io/<your-github-user>/tidalcase-agent-nginx:latest
TIDALCASE_REGISTRY_IMAGE=ghcr.io/<your-github-user>/tidalcase-registry:latest
```

If you fork the repo and enable the `.github/workflows/build.yml` workflow,
GitHub Actions will automatically publish images to
`ghcr.io/<your-github-owner>/tidalcase-<name>` on every push to `main`
(and on every release tag). In that case the `.env` overrides above are all
you need — no compose edits required.
