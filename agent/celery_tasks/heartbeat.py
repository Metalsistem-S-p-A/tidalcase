import os
import hashlib
import uuid
import celery
import requests
import docker

JOIN_TOKEN   = os.environ.get("TIDALCASE_JOIN_TOKEN", "")

if not JOIN_TOKEN:
    raise RuntimeError("TIDALCASE_JOIN_TOKEN is required")

def _system_resources() -> tuple[float, int]:
    """Return (total_cores, total_memory_mb) from the Docker host."""
    try:
        info = docker.from_env().info()
        cores = float(info.get('NCPU') or 0)
        mem_mb = int(info.get('MemTotal') or 0) // (1024 * 1024)
        return cores, mem_mb
    except Exception as e:
        print(f"[agent] system resource failed: {e}", flush=True)
        return 0.0, 0

def _load_agent_token() -> str:
    """Return this agent's stable unique identity token.

    Primary: read from /agent/data/agent_id (persisted volume).
    Fallback: derive deterministically from Docker daemon ID + JOIN_TOKEN so
    the same token is reproduced even if the volume is lost, preventing
    duplicate agent records on the manager after container recreations.
    """
    token_path = "/agent/data/agent_id"
    os.makedirs("/agent/data", exist_ok=True)
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if token:
            return token

    # Derive a stable token from the Docker daemon's own ID (stable across
    # container restarts) combined with the join token (unique per manager).
    try:
        info = docker.from_env().info()
        daemon_id = info.get('ID', '')
        if daemon_id:
            seed = f"tidalcase-network:{daemon_id}:{JOIN_TOKEN}"
            token = hashlib.sha256(seed.encode()).hexdigest()
            print(f"[agent] Derived stable token from Docker daemon ID {daemon_id[:12]}", flush=True)
        else:
            raise ValueError("empty daemon ID")
    except Exception as e:
        token = str(uuid.uuid4())
        print(f"[agent] Fallback: generated random token ({e})", flush=True)

    with open(token_path, "w", encoding="utf-8") as f:
        f.write(token)
    return token

MY_API_TOKEN = _load_agent_token()
MANAGER_URL = os.environ.get("TIDALCASE_MANAGER_URL", "").rstrip("/")

@celery.shared_task
def send_heartbeat():
    total_cores, total_memory = _system_resources()
    try:
        requests.post(
            f"{MANAGER_URL}/api/agent/heartbeat",
            headers={"Authorization": f"Bearer {MY_API_TOKEN}"},
            json={"total_cores": total_cores, "total_memory": total_memory},
            timeout=10
        )
    except Exception:
        pass
