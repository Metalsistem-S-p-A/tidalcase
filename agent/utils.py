import os
import hashlib
import uuid
import docker

JOIN_TOKEN = os.environ.get("TIDALCASE_JOIN_TOKEN", "")
MANAGER_URL = os.environ.get("TIDALCASE_MANAGER_URL", "").rstrip("/")
AGENT_URL = os.environ.get("TIDALCASE_AGENT_URL", "").strip()

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


# Stable per-agent identity token — persisted across restarts via volume mount.
MY_API_TOKEN = _load_agent_token()


def fmt_bytes(b: int) -> str:
    for unit, div in (('GiB', 1024**3), ('MiB', 1024**2), ('KiB', 1024)):
        if b >= div:
            return f"{b / div:.1f} {unit}"
    return f"{b} B"
