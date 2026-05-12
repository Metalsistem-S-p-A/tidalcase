import flask
import docker

bp = flask.Blueprint('volume', __name__)


@bp.post('/volume/ensure')
def volume_ensure():
    body = flask.request.get_json() or {}
    name = body.get('name', '')
    driver = body.get('driver') or 'local'
    driver_opts = body.get('driver_opts') or {}
    if not name:
        return flask.jsonify({"ok": False, "error": "name is required"}), 400
    created = False
    try:
        docker.from_env().volumes.get(name)
    except Exception:
        try:
            docker.from_env().volumes.create(
                name=name,
                driver=driver,
                driver_opts={k: str(v) for k, v in driver_opts.items()},
            )
            created = True
        except Exception as e:
            return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True, "created": created})
