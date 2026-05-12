import flask
import docker

bp = flask.Blueprint('prune', __name__)


@bp.post('/prune')
def prune():
    body = flask.request.get_json()
    mode = body.get('mode', 'normal')
    app_image_set = set(body.get('app_image_set', []))
    freed = 0

    try:
        result = docker.from_env().images.prune(filters={"dangling": True})
        freed += result.get('SpaceReclaimed', 0)
    except Exception as e:
        return flask.jsonify({"ok": False, "error": str(e)}), 500

    if mode == 'aggressive' and app_image_set:
        for img in docker.from_env().images.list():
            tags = img.tags
            if not tags:
                continue
            if not any(t in app_image_set for t in tags):
                try:
                    docker.from_env().images.remove(img.id, force=False, noprune=False)
                except Exception:
                    pass

    return flask.jsonify({"ok": True, "freed_bytes": freed})
