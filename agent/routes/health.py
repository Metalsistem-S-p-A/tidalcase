import psutil
import flask
import docker
bp = flask.Blueprint('health', __name__)

@bp.get('/health')
def health():
    try:
        version = docker.from_env().version().get('Version', 'unknown')
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500

    mem = psutil.virtual_memory()
    cores = psutil.cpu_count(logical=True)
    cpu_pct = psutil.cpu_percent(interval=0.1)

    return flask.jsonify({
        "ok": True,
        "docker_version": version,
        "total_cores": cores,
        "total_memory_mb": mem.total // (1024 * 1024),
        "available_memory_mb": mem.available // (1024 * 1024),
        "cpu_percent": cpu_pct,
    })
