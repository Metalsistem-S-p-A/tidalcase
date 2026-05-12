import flask
import docker

bp = flask.Blueprint('network', __name__)


@bp.post('/network/ensure')
def network_ensure():
    name = flask.request.get_json().get('name', '')
    if not name:
        return flask.jsonify({"ok": False, "error": "name is required"}), 400
    created = False
    try:
        docker.from_env().networks.get(name)
    except Exception:
        try:
            docker.from_env().networks.create(name, driver='bridge')
            created = True
        except Exception as e:
            return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True, "created": created})


@bp.post('/network/connect')
def network_connect():
    body = flask.request.get_json()
    container_name = body.get('container')
    network_name = body.get('network')
    if not container_name or not network_name:
        return flask.jsonify({"ok": False, "error": "container and network are required"}), 400
    try:
        network = docker.from_env().networks.get(network_name)
        network.connect(container_name)
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500
    return flask.jsonify({"ok": True})
