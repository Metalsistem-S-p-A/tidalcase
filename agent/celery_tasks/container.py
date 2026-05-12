import json
import os
import shutil
import time
import celery
import docker
import docker.errors
import redis
import requests
import utils


_CONFIG_DIR = '/tmp/tidalcase_configs'
_MONITOR_PREFIX = 'tidalcase:monitor:'


def _redis_client() -> redis.Redis:
    url = os.environ.get('CELERY_BROKER_URL', 'redis://tidalcase-agent-redis:6379/0')
    return redis.from_url(url, decode_responses=True)


def _notify_manager_terminated(container_name: str, reason: str) -> None:
    if not utils.MANAGER_URL:
        return
    try:
        requests.post(
            f"{utils.MANAGER_URL}/api/container/terminated",
            json={"container_name": container_name, "reason": reason},
            headers={"Authorization": f"Bearer {utils.MY_API_TOKEN}"},
            timeout=10,
        )
    except Exception as e:
        print(f"[agent] Failed to notify manager of termination: {e}", flush=True)


def _cleanup_config_files(container_name: str) -> None:
    shutil.rmtree(os.path.join(_CONFIG_DIR, container_name), ignore_errors=True)


def _delete_instance_nginx_config(name: str) -> None:
    path = os.path.join("/nginx-instances", f"{name}.conf")
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[agent] Failed to delete nginx config for '{name}': {e}", flush=True)
        return
    try:
        nginx = docker.from_env().containers.get("tidalcase-agent-nginx")
        nginx.exec_run('nginx -s reload')
    except Exception as e:
        print(f"[agent] nginx reload error: {e}", flush=True)


@celery.shared_task(queue='monitor')
def pull_image(image: str) -> None:
    r = _redis_client()
    key = f"tidalcase:pull:{image}"
    layers_total: set = set()
    layers_done: set = set()
    r.set(key, json.dumps({"status": "pulling", "percent": 0, "layers_done": 0, "layers_total": 0}), ex=3600)
    print(f"[agent] Auto-pulling '{image}'...", flush=True)
    try:
        for event in docker.from_env().api.pull(image, stream=True, decode=True):
            status = event.get('status', '')
            layer_id = event.get('id', '')
            if layer_id and status in ('Pulling fs layer', 'Waiting'):
                layers_total.add(layer_id)
            elif layer_id and status in ('Pull complete', 'Already exists'):
                layers_done.add(layer_id)
            total = len(layers_total)
            done = len(layers_done)
            percent = min(int(done / total * 100), 99) if total > 0 else 0
            r.set(key, json.dumps({
                "status": "pulling", "percent": percent,
                "layers_done": done, "layers_total": total,
            }), ex=3600)
        r.set(key, json.dumps({"status": "done", "percent": 100}), ex=300)
        print(f"[agent] '{image}' pulled OK", flush=True)
    except Exception as e:
        r.set(key, json.dumps({"status": "error", "percent": 0, "error": str(e)}), ex=300)
        print(f"[agent] Pull failed for '{image}': {e}", flush=True)


@celery.shared_task(queue='monitor')
def monitor_container(container_name: str, session_time_limit_s: int) -> None:
    """Register a container for monitoring. Actual checks are done by check_containers."""
    deadline = time.time() + session_time_limit_s if session_time_limit_s else None
    record = json.dumps({"deadline": deadline})
    # TTL: keep in Redis for at least the session limit + 1 hour as a safety net
    ttl = (session_time_limit_s + 3600) if session_time_limit_s else None
    r = _redis_client()
    r.set(f"{_MONITOR_PREFIX}{container_name}", record, ex=ttl)
    print(f"[agent] Monitoring '{container_name}' (limit={session_time_limit_s}s)", flush=True)


@celery.shared_task(queue='monitor')
def check_containers() -> None:
    """Periodic task: scan all monitored containers for exit or timeout."""
    r = _redis_client()
    keys = list(r.scan_iter(f"{_MONITOR_PREFIX}*"))
    if not keys:
        return

    docker_client = docker.from_env()
    now = time.time()

    for key in keys:
        raw = r.get(key)
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except Exception:
            r.delete(key)
            continue

        container_name = key[len(_MONITOR_PREFIX):]
        deadline = record.get('deadline')

        if deadline and now >= deadline:
            print(f"[agent] Session timeout for '{container_name}', killing", flush=True)
            try:
                container = docker_client.containers.get(container_name)
                container.kill()
                container.remove(force=True)
            except Exception:
                pass
            r.delete(key)
            _notify_manager_terminated(container_name, "timeout")
            _cleanup_config_files(container_name)
            _delete_instance_nginx_config(container_name)
            continue

        try:
            container = docker_client.containers.get(container_name)
            container.reload()
            if container.status not in ('running', 'restarting', 'created'):
                oom = container.attrs.get('State', {}).get('OOMKilled', False)
                exit_code = container.attrs.get('State', {}).get('ExitCode', '?')
                label = 'OOM-killed' if oom else f'exited (code={exit_code})'
                print(f"[agent] Container '{container_name}' {label} status={container.status}", flush=True)
                try:
                    logs = container.logs(tail=60).decode('utf-8', errors='replace').strip()
                    if logs:
                        print(f"[agent] Last logs for '{container_name}':\n{logs}", flush=True)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                r.delete(key)
                _notify_manager_terminated(container_name, "oom" if oom else "exited")
                _cleanup_config_files(container_name)
                _delete_instance_nginx_config(container_name)
        except docker.errors.NotFound:
            print(f"[agent] Container '{container_name}' gone (removed externally)", flush=True)
            r.delete(key)
            _notify_manager_terminated(container_name, "removed")
            _cleanup_config_files(container_name)
            _delete_instance_nginx_config(container_name)
        except Exception as e:
            print(f"[agent] Monitor error for '{container_name}': {e}", flush=True)
