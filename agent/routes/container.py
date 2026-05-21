import json
import os
import time
import socket
import shutil
import psutil
import flask
import docker.errors
import redis as redis_lib
import celery_tasks.container
import utils

def _redis_client():
    url = os.environ.get('CELERY_BROKER_URL', 'redis://tidalcase-redis:6379/1')
    return redis_lib.from_url(url, decode_responses=True)

bp = flask.Blueprint('container', __name__)

def _parse_mem_bytes(s) -> int:
    if not s:
        return 0
    s = str(s).strip().lower()
    units = {'b': 1, 'k': 1024, 'm': 1024**2, 'g': 1024**3}
    for suffix, mult in units.items():
        if s.endswith(suffix):
            try:
                return int(float(s[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(s)
    except ValueError:
        return 0

# CONFIG_DIR: path inside this agent container where config files are written.
# CONFIG_HOST_DIR: same directory as seen by the Docker HOST daemon — used as
#   bind-mount source when spawning KasmVNC containers.  On Linux same-machine
#   deployments these are identical; on Windows/remote they differ.
CONFIG_DIR = '/tmp/tidalcase_configs'
CONFIG_HOST_DIR = os.environ.get('TIDALCASE_CONFIG_HOST_DIR', CONFIG_DIR)
CERTS_HOST_DIR  = os.environ.get('TIDALCASE_CERTS_HOST_DIR')
AGENT_URL   = os.environ.get("TIDALCASE_AGENT_URL", "").strip()

_TEMPLATE_PATH      = os.path.join(os.path.dirname(__file__), '..', 'container_template.conf')
_GUAC_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'guac_template.conf')


def _write_guac_nginx_config(name: str, upstream_ip: str) -> None:
    instance_id = name.removeprefix('tidalcase-')
    with open(_GUAC_TEMPLATE_PATH, "r", encoding="utf-8") as t:
        config = t.read().replace("{instance_id}", instance_id).replace("{upstream_ip}", upstream_ip)
    os.makedirs("/nginx-instances", exist_ok=True)
    with open(os.path.join("/nginx-instances", f"{name}.conf"), 'w', encoding="utf-8") as f:
        f.write(config)
    _reload_nginx()


def _write_instance_nginx_config(name: str, auth_header: str, upstream_ip: str) -> None:
    instance_id = name.removeprefix('tidalcase-')
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as t:
        template = t.read()
        config = (template
                .replace("{instance_id}", instance_id)
                .replace("{upstream_ip}", upstream_ip)
                .replace("{auth_header}", auth_header))
        os.makedirs("/nginx-instances", exist_ok=True)
        with open(os.path.join("/nginx-instances", f"{name}.conf"), 'w', encoding="utf-8") as f:
            f.write(config)
        _reload_nginx()


def _delete_instance_nginx_config(name: str) -> None:
    path = os.path.join("/nginx-instances", f"{name}.conf")
    try:
        os.remove(path)
        _reload_nginx()
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[agent] Failed to delete nginx config for '{name}': {e}", flush=True)


def _wait_for_port(host: str, port: int, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Poll until the TCP port is accepting connections or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(interval)
    return False


def _wait_for_ip(container, network: str, timeout: float = 10.0, interval: float = 0.25) -> str:
    """Poll container reload until an IP is assigned on the given network."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        container.reload()
        nets = container.attrs.get('NetworkSettings', {}).get('Networks', {})
        ip = nets.get(network, {}).get('IPAddress', '') or None
        if ip:
            return ip
        time.sleep(interval)
    return None


def _reload_nginx() -> None:
    try:
        nginx = docker.from_env().containers.get("tidalcase-agent-nginx")
        test = nginx.exec_run('nginx -t')
        if test.exit_code != 0:
            print(f"[agent] nginx config test FAILED:\n{test.output.decode(errors='replace')}", flush=True)
            return
        result = nginx.exec_run('nginx -s reload')
        if result.exit_code != 0:
            print(f"[agent] nginx reload signal failed: {result.output}", flush=True)
    except Exception as e:
        print(f"[agent] nginx reload error: {e}", flush=True)


def _write_config_files(container_name: str, config_files: list) -> dict:
    """Write config files to disk; return Docker bind-mount volumes dict."""
    if not config_files:
        return {}
    base_container = os.path.join(CONFIG_DIR,      container_name)
    base_host      = os.path.join(CONFIG_HOST_DIR, container_name)
    os.makedirs(base_container, exist_ok=True)
    volumes = {}
    for cf in config_files:
        target = cf['path']
        safe   = target.replace('/', '_').lstrip('_')
        host_write = os.path.join(base_container, safe)
        host_mount = os.path.join(base_host,      safe)
        with open(host_write, 'w', encoding="utf-8") as fh:
            fh.write(cf['content'])
        os.chmod(host_write, 0o644)
        volumes[host_mount] = {'bind': target, 'mode': 'ro'}
    return volumes


def _cleanup_config_files(container_name: str) -> None:
    shutil.rmtree(os.path.join(CONFIG_DIR, container_name), ignore_errors=True)


@bp.post('/container/run')
def container_run():
    body = flask.request.get_json()
    image                = body.get('image')
    name                 = body.get('name')
    env                  = body.get('env', {})
    mem_limit            = body.get('mem_limit')
    memswap_limit        = body.get('memswap_limit')
    cpu_shares           = body.get('cpu_shares', 1024)
    network              = body.get('network')
    ports                = body.get('ports')
    mounts               = body.get('mounts', [])
    config_files         = body.get('config_files', [])
    shm_size             = body.get('shm_size')
    extra_hosts          = body.get('extra_hosts', {})
    session_time_limit_s = body.get('session_time_limit_s')
    auth_header          = body.get('auth_header', '')

    if mem_limit:
        mem_bytes = _parse_mem_bytes(mem_limit)
        swap_extra_bytes = _parse_mem_bytes(memswap_limit) if memswap_limit else 0
        avail_ram = psutil.virtual_memory().available
        avail_swap = psutil.swap_memory().free
        if avail_ram < mem_bytes:
            return flask.jsonify({
                "ok": False,
                "error": f"Insufficient memory: need {utils.fmt_bytes(mem_bytes)}, available {utils.fmt_bytes(avail_ram)}",
            }), 507
        if swap_extra_bytes > 0 and avail_swap < swap_extra_bytes:
            return flask.jsonify({
                "ok": False,
                "error": f"Insufficient swap: need {utils.fmt_bytes(swap_extra_bytes)} extra, available {utils.fmt_bytes(avail_swap)}",
            }), 507

    kwargs = {
        "image": image,
        "name": name,
        "environment": env,
        "detach": True,
        "extra_hosts": extra_hosts,
        "network": "tidalcase-network"
    }

    if mem_limit:
        kwargs['mem_limit'] = mem_limit
        if memswap_limit:
            swap_extra = _parse_mem_bytes(memswap_limit)
            if swap_extra > 0:
                kwargs['memswap_limit'] = _parse_mem_bytes(mem_limit) + swap_extra
    if cpu_shares:
        kwargs['cpu_shares'] = cpu_shares
    if shm_size:
        kwargs['shm_size'] = shm_size
    if ports:
        kwargs['ports'] = ports
    if network:
        kwargs['network'] = network

    volumes = {}
    for m in mounts:
        volumes[m['source']] = {'bind': m['target'], 'mode': 'rw'}
    volumes.update(_write_config_files(name, config_files))
    if CERTS_HOST_DIR:
        volumes[CERTS_HOST_DIR] = {'bind': '/certs', 'mode': 'ro'}
    if volumes:
        kwargs['volumes'] = volumes

    try:
        docker.from_env().images.get(image)
        image_exists = True
    except docker.errors.ImageNotFound:
        image_exists = False

    # If image exists locally, check whether we just finished a pull for it.
    # A fresh "done" entry in Redis (TTL 300 s) means the pull just completed
    # and the local image is up to date — proceed to run. In all other cases
    # (no entry, expired, or still pulling) queue a new pull so stale :latest
    # images are always refreshed before the container starts.
    if image_exists:
        try:
            raw = _redis_client().get(f"tidalcase:pull:{image}")
            if raw and json.loads(raw).get('status') == 'done':
                pass  # fresh pull — image is current, fall through to run
            else:
                image_exists = False  # treat as missing to trigger pull
        except Exception:
            pass  # Redis unavailable — run with whatever is local

    if not image_exists:
        _cleanup_config_files(name)
        celery_tasks.container.pull_image.delay(image)
        return flask.jsonify({
            "ok": False,
            "pulling": True,
            "error": "Image pull in progress, retry shortly"
        }), 202

    try:
        container = docker.from_env().containers.run(**kwargs)
    except Exception as e:
        _cleanup_config_files(name)
        return flask.jsonify({"ok": False, "error": str(e)}), 500

    container.reload()
    published = {}
    if ports and container.ports:
        for p, bindings in container.ports.items():
            if bindings:
                published[p] = bindings[0]['HostPort']

    celery_tasks.container.monitor_container.delay(name, int(session_time_limit_s) if session_time_limit_s else 0)

    agent_network = "tidalcase-network"
    # Ensure the container is on the agent network; connect explicitly if needed.
    nets = container.attrs.get('NetworkSettings', {}).get('Networks', {})
    if agent_network not in nets:
        try:
            docker.from_env().networks.get(agent_network).connect(container)
            print(f"[agent] Connected '{name}' to {agent_network}", flush=True)
        except Exception as e:
            print(f"[agent] Network connect failed for '{name}': {e}", flush=True)

    ip = _wait_for_ip(container, agent_network, timeout=10.0)
    print(f"[agent] Container '{name}' IP on {agent_network}: {ip}", flush=True)

    vnc_url  = None
    guac_url = None
    instance_id = name.removeprefix('tidalcase-')

    if auth_header and ip:
        ws_path = f"/desktop/{instance_id}/vnc/websockify"
        vnc_url = (
            f"{AGENT_URL}/desktop/{instance_id}/vnc/vnc.html"
            f"?cursor=true&autoconnect=true&resize=remote"
            f"&clipboard_up=true&clipboard_down=true&clipboard_seamless=true&toggle_control_panel=false"
            f"&path={ws_path}"
        )
        _write_instance_nginx_config(name, auth_header, ip)
        ready = _wait_for_port(ip, 6901, timeout=30.0)
        if not ready:
            print(f"[agent] Warning: container '{name}' port 6901 not ready after 30 s", flush=True)
        else:
            print(f"[agent] Container '{name}' ready on port 6901", flush=True)
    elif auth_header:
        print(f"[agent] Warning: no IP for '{name}' on {agent_network}, nginx config not written", flush=True)

    if env.get('GUAC_KEY') and ip:
        guac_url = f"{AGENT_URL}/desktop/{instance_id}/guac/"
        _write_guac_nginx_config(name, ip)
        ready = _wait_for_port(ip, 8080, timeout=30.0)
        if not ready:
            print(f"[agent] Warning: guac container '{name}' port 8080 not ready after 30 s", flush=True)
        else:
            print(f"[agent] Guac container '{name}' ready on port 8080", flush=True)
    elif env.get('GUAC_KEY'):
        print(f"[agent] Warning: no IP for guac container '{name}', nginx config not written", flush=True)

    return flask.jsonify({
        "ok": True,
        "container_id": container.short_id,
        "status": container.status,
        "published_ports": published,
        "vnc_url": vnc_url,
        "guac_url": guac_url,
    })

@bp.get('/container/<name>')
def container_exists(name):
    try:
        docker.from_env().containers.get(name)
    except docker.errors.NotFound:
        return flask.jsonify({"ok": False, "error": "not found"}), 404
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    
    return flask.jsonify({"ok": True})

@bp.post('/container/<name>/pause')
def container_pause(name):
    try:
        docker.from_env().containers.get(name).pause()
    except docker.errors.NotFound:
        return flask.jsonify({"ok": False, "error": "not found"}), 404
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True})


@bp.post('/container/<name>/unpause')
def container_unpause(name):
    try:
        docker.from_env().containers.get(name).unpause()
    except docker.errors.NotFound:
        return flask.jsonify({"ok": False, "error": "not found"}), 404
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True})


@bp.delete('/container/<name>')
def container_remove(name):
    try:
        container = docker.from_env().containers.get(name)
        container.remove(force=True, v=True)
    except docker.errors.NotFound:
        return flask.jsonify({"ok": False, "error": "not found"}), 404
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    _cleanup_config_files(name)
    _delete_instance_nginx_config(name)
    try:
        _redis_client().delete(f"tidalcase:monitor:{name}")
    except Exception:
        pass
    return flask.jsonify({"ok": True})


@bp.get('/container/<name>/ip')
def container_ip(name):
    network = flask.request.args.get('network', 'tidalcase-network')
    try:
        container = docker.from_env().containers.get(name)
        container.reload()
        nets = container.attrs.get('NetworkSettings', {}).get('Networks', {})
        ip = nets.get(network, {}).get('IPAddress') or None
    except docker.errors.NotFound:
        return flask.jsonify({"ok": False, "error": "not found"}), 404
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True, "ip": ip})


@bp.get('/image/pull/status')
def pull_status():
    image = flask.request.args.get('image', '')
    if not image:
        return flask.jsonify({"ok": False, "error": "image required"}), 400
    try:
        raw = _redis_client().get(f"tidalcase:pull:{image}")
    except Exception:
        return flask.jsonify({"ok": True, "status": "unknown"})
    if not raw:
        return flask.jsonify({"ok": True, "status": "unknown"})
    try:
        return flask.jsonify({"ok": True, **json.loads(raw)})
    except Exception:
        return flask.jsonify({"ok": True, "status": "unknown"})


@bp.post('/image/pull')
def pull_images():
    body = flask.request.get_json()
    image = body.get('image')
    celery_tasks.container.pull_image.delay(image)