"""
Endpoints called BY agents (no user session required — token-based auth).

  POST /api/agent/register           — agent self-registers using the manager's join token
  POST /api/agent/heartbeat          — agent signals it is alive
  POST /api/container/terminated     — agent reports a container has stopped (exit or timeout)
"""
import datetime
import flask
import app.models.agent
import app.models.tide
import app.utils.extensions
import app.utils.logger
import app.routes.tide
import app.utils.setup

agent_api_bp = flask.Blueprint('agent_api', __name__)


def _agent_from_bearer() -> app.models.agent.Agent | None:
    """Resolve and return the Agent from the Bearer token in the current request."""
    auth = flask.request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    return app.models.agent.Agent.query.filter_by(api_token=token).first()


@agent_api_bp.post('/api/agent/register')
def agent_register():
    body = flask.request.get_json() or {}
    join_token    = body.get('join_token', '')
    api_token     = body.get('api_token', '')
    agent_url     = body.get('agent_url', '')
    agent_name    = body.get('agent_name', 'unnamed-agent')
    total_cores   = body.get('total_cores')
    total_memory  = body.get('total_memory')

    # Validate manager's join token (one per manager, shared by all agents)
    expected = app.utils.setup.get_join_token()
    if not expected or join_token != expected:
        return flask.jsonify({"ok": False, "error": "Invalid join token"}), 401

    if not api_token:
        return flask.jsonify({"ok": False, "error": "api_token is required"}), 400

    # Primary lookup: by api_token (stable identity).
    agent = app.models.agent.Agent.query.filter_by(api_token=api_token).first()
    app.utils.logger.log("DEBUG", f"agent_register: token={api_token[:8]}… found_by_token={agent is not None}")

    # Fallback lookups when the token changed (e.g. volume lost between restarts).
    if not agent and agent_url:
        agent = app.models.agent.Agent.query.filter_by(api_url=agent_url).first()
        if agent:
            app.utils.logger.log("INFO", f"Agent '{agent.display_name}' re-adopted by URL (token rotated)")
            agent.api_token = api_token

    if not agent:
        app.utils.logger.log("INFO", f"agent_register: NEW record — name='{agent_name}' url={agent_url}")
        agent = app.models.agent.Agent(
            display_name=agent_name,
            docker_host='',
            api_url=agent_url,
            api_token=api_token,
            total_cores=total_cores,
            total_memory=total_memory,
        )
        app.utils.extensions.db.session.add(agent)
    else:
        app.utils.logger.log("DEBUG", f"agent_register: UPDATE existing '{agent.display_name}' (id={agent.id}) — name NOT touched")
        if agent_url:
            agent.api_url = agent_url
        if total_cores is not None:
            agent.total_cores = total_cores
        if total_memory is not None:
            agent.total_memory = total_memory

    agent.healthy = True
    agent.last_healthcheck_at = datetime.datetime.now()
    try:
        app.utils.extensions.db.session.commit()
    except Exception:
        app.utils.extensions.db.session.rollback()
        agent = app.models.agent.Agent.query.filter_by(api_token=api_token).first()
        if not agent:
            return flask.jsonify({"ok": False, "error": "Registration conflict"}), 409
    return flask.jsonify({"ok": True, "agent_id": agent.id})


@agent_api_bp.post('/api/agent/heartbeat')
def agent_heartbeat():
    agent = _agent_from_bearer()
    if not agent:
        return flask.jsonify({"ok": False, "error": "Unauthorized"}), 401

    body = flask.request.get_json() or {}
    total_cores = body.get('total_cores')
    total_memory = body.get('total_memory')
    if total_cores is not None:
        agent.total_cores = total_cores
    if total_memory is not None:
        agent.total_memory = total_memory
    agent.healthy = True
    agent.last_healthcheck_at = datetime.datetime.now()
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"ok": True})


@agent_api_bp.post('/api/container/terminated')
def container_terminated():
    agent = _agent_from_bearer()
    if not agent:
        return flask.jsonify({"ok": False, "error": "Unauthorized"}), 401

    body = flask.request.get_json() or {}
    container_name = body.get('container_name', '')
    reason = body.get('reason', 'exited')

    # Extract instance_id from container name
    prefix = 'tidalcase-'
    if not container_name.startswith(prefix):
        return flask.jsonify({"ok": False, "error": "Invalid container_name"}), 400
    instance_id = container_name[len(prefix):]

    instance = app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        # Already cleaned up — idempotent
        return flask.jsonify({"ok": True, "note": "instance already gone"})

    app.utils.logger.log("INFO", f"Agent '{agent.display_name}' reports container '{container_name}' terminated ({reason})")
    app.routes.tide._destroy_instance(instance, remove_container=False)
    return flask.jsonify({"ok": True})
