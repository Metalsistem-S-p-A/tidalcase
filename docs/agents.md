# Agents

A Tidalcase **agent** is a small Flask + Celery service that runs on a Docker
host and is responsible for actually launching, monitoring and tearing down
tide containers there. The manager never starts containers directly: it
delegates to agents.

This split exists so you can scale out (more agents = more concurrent
sessions), isolate workloads on dedicated hardware (GPU hosts, high-memory
hosts), and survive the loss of a single host without taking the manager
down.

## What an agent host looks like

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent host (any Linux box with Docker)                         │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │ tidalcase-agent  │  │  agent-nginx     │  │  agent       │   │
│  │  (Flask API)     │  │  :7443           │  │  Celery      │   │
│  │  Celery beat     │  │                  │  │  worker      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
│         │                       │                    │          │
│         └───────────────────────┴────────────────────┘          │
│                       /var/run/docker.sock                      │
│                                                                 │
│  Docker engine ───► tide session ─── tide session ─── …          │
└─────────────────────────────────────────────────────────────────┘
```

The agent talks to the manager over Redis (Celery queues) and HTTPS. The
browser talks to the agent's **nginx on port 7443** for the WebSocket VNC
stream — that traffic does not go through the manager.

## Adding an agent

### 1. Issue a join token on the manager

In the manager UI, go to **Admin → Agents → Add agent**. Tidalcase generates
a single-use join token and shows you the agent's expected URL. Copy them
both.

You can also read the bootstrap join token from disk:

```bash
docker compose exec tidalcase-backend cat /app/data/join_token
```

That token is the one used for the first agent registration; the admin UI is
the preferred way to mint additional tokens.

### 2. Prepare the agent host

The agent needs:

- Docker Engine 24+ and Compose v2.
- Inbound TCP 7443 reachable from your users (this is where the VNC
  WebSocket lands).
- Outbound HTTPS to the manager URL.
- TLS certs at `/etc/tidalcase/certs/` (the agent's nginx uses them on
  7443). For internal-only setups, a self-signed cert is fine.
- A config directory at `/etc/tidalcase/configs/` (created automatically on
  first start; agent writes per-session nginx vhosts there).

### 3. Bring up the agent stack

```bash
git clone https://github.com/<your-org>/tidalcase.git
cd tidalcase
cp .env.example .env
```

Edit `.env` and set, at minimum:

```env
TIDALCASE_JOIN_TOKEN=<token from step 1>
TIDALCASE_MANAGER_URL=https://tidalcase.example.com
TIDALCASE_AGENT_URL=https://this-agent.example.com:7443
```

Then:

```bash
docker compose --profile agent up -d
```

The agent registers itself with the manager on startup. Within a few seconds
it appears in **Admin → Agents** as **Online**.

> [!NOTE]
> The agent profile services share the same `tidalcase-network` and Redis
> instance as the manager. If your agent is on a **separate host**, the
> bundled Redis won't be reachable — you'll want an external Redis or a
> network plan that lets the agent reach the manager's Redis. Most real
> deployments run the manager and at least one agent on the **same host**,
> and add remote agents only when they need scale or isolation.

### 4. Verify

From the manager:

```bash
docker compose logs -f tidalcase-celery-worker | grep -i heartbeat
```

You should see periodic heartbeat tasks from the agent. From the agent host:

```bash
docker compose --profile agent logs -f tidalcase-agent
```

Look for `registered with manager` and subsequent heartbeats.

## How scheduling works

When a user launches a tide:

1. The frontend POSTs to the backend.
2. The backend looks up the tide's allowed agents (a tide can be pinned to
   specific agents) and picks one with capacity (free cores/memory tracked
   from heartbeats).
3. The backend dispatches a Celery task to the chosen agent's queue.
4. The agent's Celery worker pulls the image (if needed), creates the
   container, generates a random VNC password, writes an nginx vhost file
   under `vnc-nginx-instances`, and signals the agent's nginx to reload.
5. The backend gets the result, stores it as a `TideInstance`, and returns
   the session URL to the user.
6. The browser opens that URL — handled by the agent's nginx — and the VNC
   WebSocket flows directly between the user and the tide container.

## Capacity tracking

Each heartbeat the agent reports:

- Total and free CPU cores
- Total and free memory
- Running tide containers (by ID)
- Docker engine version

The manager uses these to refuse launches when an agent is full and to show
load in the **Admin → Agents** view.

## Maintenance

From **Admin → Agents → <agent> → Actions** you can:

- **Drain** — stop scheduling new sessions to this agent. Existing sessions
  keep running.
- **Prune** — ask the agent to `docker system prune` (with safeguards
  against pruning live tide containers). Triggered as a Celery task.
- **Deregister** — remove the agent from the manager. The agent host itself
  is not touched; bring it down with `docker compose --profile agent down`.

## Rotating join tokens

The manager generates fresh join tokens on demand from
**Admin → Agents → Add agent**. The bootstrap token in
`/app/data/join_token` is regenerated if you delete it and restart the
backend (it'll only be used for the very first agent registration in most
flows).

If a token leaks (it was committed to Git, ended up in a screenshot, etc.):

1. Mint a new one in the admin UI.
2. Revoke any agents you don't recognise from **Admin → Agents**.
3. Rotate the bootstrap token if it's the one that leaked:

   ```bash
   docker compose exec tidalcase-backend rm /app/data/join_token
   docker compose restart tidalcase-backend
   ```
