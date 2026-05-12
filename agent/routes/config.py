import flask

bp = flask.Blueprint('config', __name__)

agent_config = {"prune_mode": "off", "app_image_set": []}

@bp.post('/config')
def set_config():
    body = flask.request.get_json() or {}

    prune_mode = body.get('prune_mode')
    if prune_mode in ('off', 'normal', 'aggressive'):
        agent_config['prune_mode'] = prune_mode

    app_image_set = body.get('app_image_set')
    if isinstance(app_image_set, list):
        agent_config['app_image_set'] = app_image_set

    return flask.jsonify({"ok": True})
