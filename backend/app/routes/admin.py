import json
import platform
import re
import sys
import os
import datetime
import uuid
import urllib.parse
import flask
import app.utils.jwt_validator
import requests
import app.utils.docker
import app.utils.extensions
import app.utils.permissions
import app.models.tide
import app.models.user
import app.models.agent
import app.models.registry
import app.models.storage
import app.utils.extensions
import app.utils.agent_client
import app.routes.auth

admin_bp = flask.Blueprint('admin', __name__)

_MEM_RE = re.compile(r'^\d+(\.\d+)?[bkmgBKMG]$')

def _parse_mem_bytes(s: str) -> int:
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

def get_container_ip(container, tide):
    """Get the IP address of a container, prioritizing the default network for nginx connectivity"""
    networks = container.attrs['NetworkSettings']['Networks']

    if tide.container_network and tide.container_network in networks:
        return networks[tide.container_network]['IPAddress']

    for network_name in ['default_network', 'bridge']:
        if network_name in networks and networks[network_name]['IPAddress']:
            return networks[network_name]['IPAddress']

    return "N/A"

@admin_bp.get('/system_info')
@app.utils.jwt_validator.jwt_required
def api_admin_system():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    nginx_version = app.utils.docker.get_nginx_version()

    response = {
        "success": True,
        "system": {
            "hostname": os.popen("hostname").read().strip(),
            "os": f"{platform.system()} {platform.release()}"
        },
        "version": {
            "tidalcase": app.__version__,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "docker": app.utils.docker.get_docker_version(),
            "nginx": nginx_version,
        },
    }

    return flask.jsonify(response)

@admin_bp.get('/users')
@app.utils.jwt_validator.jwt_required
def api_admin_users():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_USERS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    users =  app.models.user.User.query.order_by( app.models.user.User.created_at.asc()).all()

    data = []
    for user in users:
        data.append({
            "id": user.id,
            "username": user.username,
            "usertype": user.usertype,
            "protected": user.protected,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "groups": [{"id": str(g.id), "display_name": g.display_name} for g in user.groups],
            "auto_start_tide_id": user.auto_start_tide_id,
            "preferred_language": user.preferred_language
        })

    return flask.jsonify({"data": data, "totalRecords": len(data)})

@admin_bp.get('/instances')
@app.utils.jwt_validator.jwt_required
def api_admin_instances():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_INSTANCES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    instances =  app.models.tide.TideInstance.query.all()

    response = {
        "success": True,
        "instances": []
    }

    for instance in instances:
        tide =  app.models.tide.Tide.query.filter_by(id=instance.tide_id).first()
        user =  app.models.user.User.query.filter_by(id=instance.user_id).first()
        agent =  app.models.agent.Agent.query.filter_by(id=instance.agent_id).first()

        response["instances"].append({
            "id": instance.id,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
            "tide": {
                "id": tide.id,
                "display_name": tide.display_name,
                "description": tide.description,
                "container_docker_image": tide.container_docker_image,
                "container_docker_registry": tide.container_docker_registry,
                "container_cores": tide.container_cores,
                "container_memory": tide.container_memory,
                "container_network": tide.container_network,
                "image_path": tide.image_path
            },
            "user": {
                "id": user.id,
                "username": user.username
            },
            "agent": {
                "name": agent.display_name
            }
        })

    return flask.jsonify(response)

@admin_bp.get('/tides')
@app.utils.jwt_validator.jwt_required
def api_admin_tides():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    tides =  app.models.tide.Tide.query.all()
    tides = sorted(tides, key=lambda x: x.display_name)

    response = {
        "success": True,
        "tides": []
    }

    for tide in tides:
        response["tides"].append({
            "id": tide.id,
            "display_name": tide.display_name,
            "description": tide.description,
            "image_path": tide.image_path,
            "tide_type": tide.tide_type,
            "container_docker_image": tide.container_docker_image,
            "container_docker_registry": tide.container_docker_registry,
            "container_cores": tide.container_cores,
            "container_memory": tide.container_memory,
            "container_swap": tide.container_swap,
            "container_network": tide.container_network,
            "server_ip": tide.server_ip,
            "server_port": tide.server_port,
            "restricted_groups": tide.restricted_groups,
            "session_time_limit": tide.session_time_limit or 0,
            "session_idle_time_limit": tide.session_idle_time_limit or 0,
            "agent_selection_mode": tide.agent_selection_mode or 'auto',
            "agents": [{"id": a.id, "display_name": a.display_name} for a in (tide.agents or [])],
            "vnc_user": tide.vnc_user or 'kasm_user',
            "upload_path": tide.upload_path or '',
            "download_path": tide.download_path or '',
            'open_mode': tide.open_mode or 'user',
            'connection_settings': tide.connection_settings or {}
        })

    return flask.jsonify(response)

@admin_bp.post('/tide')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_tide():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    tide_id = flask.request.json.get('id')
    tide =  app.models.tide.Tide.query.filter_by(id=tide_id).first()

    create_new = False
    if not tide or tide_id == "null":
        create_new = True
        tide =  app.models.tide.Tide()

    tide.description = flask.request.json.get('description', None)
    if tide.description == "":
        tide.description = None
    tide.image_path = flask.request.json.get('image_path', None)
    if tide.image_path == "":
        tide.image_path = None

    restricted_groups = flask.request.json.get('restricted_groups', [])
    if restricted_groups:
        tide.restricted_groups = ','.join(restricted_groups)
    else:
        tide.restricted_groups = None

    tide.display_name = flask.request.json.get('display_name')
    if not tide.display_name:
        return flask.jsonify({"success": False, "error": "Display Name is required"}), 400

    tide.tide_type = flask.request.json.get('tide_type')
    if not tide.tide_type:
        return flask.jsonify({"success": False, "error": " app.models.tide.Tide Type is required"}), 400

    tide.container_docker_registry = flask.request.json.get('container_docker_registry', None)

    tide.container_docker_image = flask.request.json.get('container_docker_image')
    if not tide.container_docker_image:
        return flask.jsonify({"success": False, "error": "Docker Image is required"}), 400

    if tide.tide_type == "container":

        if not flask.request.json.get('container_cores'):
            return flask.jsonify({"success": False, "error": "Cores is required"}), 400

        raw_memory = str(flask.request.json.get('container_memory') or '').strip()
        if not raw_memory:
            return flask.jsonify({"success": False, "error": "Memory is required"}), 400
        if not _MEM_RE.match(raw_memory):
            return flask.jsonify({"success": False, "error": "Memory must be a Docker memory string (e.g. 512m, 2g)"}), 400

        raw_swap = str(flask.request.json.get('container_swap') or '').strip()
        if raw_swap and not _MEM_RE.match(raw_swap):
            return flask.jsonify({"success": False, "error": "Swap must be a Docker memory string (e.g. 1g, 512m)"}), 400

        try:
            tide.container_cores = float(flask.request.json.get('container_cores'))
        except Exception:
            return flask.jsonify({"success": False, "error": "Cores must be a number"}), 400

        if tide.container_cores < 0:
            return flask.jsonify({"success": False, "error": "Cores cannot be negative"}), 400

        tide.container_memory = raw_memory.lower()
        tide.container_swap = raw_swap.lower() if raw_swap else None

        tide.container_network = flask.request.json.get('container_network')
        if not tide.container_network:
            tide.container_network = None

    elif tide.tide_type in ("vnc", "rdp", "ssh"):
        tide.server_ip = flask.request.json.get('server_ip')
        if not tide.server_ip:
            return flask.jsonify({"success": False, "error": "Server IP is required"}), 400

        tide.server_port = flask.request.json.get('server_port') or None

        tide.container_cores = 1
        tide.container_memory = '512m'
        tide.container_swap = None

    try:
        tide.session_time_limit = int(flask.request.json.get('session_time_limit', 0))
    except (TypeError, ValueError):
        tide.session_time_limit = 0
    try:
        tide.session_idle_time_limit = int(flask.request.json.get('session_idle_time_limit', 0))
    except (TypeError, ValueError):
        tide.session_idle_time_limit = 0

    mode = flask.request.json.get('agent_selection_mode', 'auto') or 'auto'
    tide.agent_selection_mode = mode if mode in ('auto', 'fixed', 'rr', 'll') else 'auto'
    agent_ids = flask.request.json.get('agent', []) or []
    tide.agents = app.models.agent.Agent.query.filter(app.models.agent.Agent.id.in_(agent_ids)).all() if agent_ids else []
    tide.vnc_user = flask.request.json.get('vnc_user') or None
    tide.upload_path = flask.request.json.get('upload_path') or None
    tide.download_path = flask.request.json.get('download_path') or None
    tide.open_mode = flask.request.json.get('open_mode') or 'user'
    tide.connection_settings = flask.request.json.get('connection_settings') or {}

    if create_new:
        app.utils.extensions.db.session.add(tide)

    app.utils.extensions.db.session.commit()

    return flask.jsonify({
        "success": True,
        "tide_id": tide.id
    })

@admin_bp.delete('/tide')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_tide():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    tide_id = flask.request.json.get('id')
    tide =  app.models.tide.Tide.query.filter_by(id=tide_id).first()
    if not tide:
        return flask.jsonify({"success": False, "error": " app.models.tide.Tide not found"}), 404

    instances =  app.models.tide. app.models.tide.TideInstance.query.filter_by(tide_id=tide_id).all()

    for instance in instances:
        agent = app.models.agent.Agent.query.filter_by(id=instance.agent_id).first()
        if agent:
            client: app.utils.agent_client.AgentHTTPClient = app.utils.docker.get_agent_client(agent)
            if client:
                client.remove_container(f'tidalcase-{instance.id}')

        app.utils.extensions.db.session.delete(instance)
    app.utils.extensions.db.session.commit()

    app.utils.extensions.db.session.delete(tide)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.delete('/instance')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_instance():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_INSTANCES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    instance_id = flask.request.json.get('id')
    instance =  app.models.tide. app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        return flask.jsonify({"success": False, "error": "Instance not found"}), 404

    agent = app.models.agent.Agent.query.filter_by(id=instance.agent_id).first()
    if agent:
        client: app.utils.agent_client.AgentHTTPClient = app.utils.docker.get_agent_client(agent)
        if client:
            client.remove_container(f'tidalcase-{instance.id}')

    app.utils.extensions.db.session.delete(instance)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.post('/user')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_user():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_USERS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    user_id = flask.request.json.get('id')
    user =  app.models.user.User.query.filter_by(id=user_id).first()

    create_new = False
    if not user or user_id == "null":
        create_new = True
        user =  app.models.user.User()

    username = flask.request.json.get('username')
    if not username:
        return flask.jsonify({"success": False, "error": " app.models.user.Username is required"}), 400
    if " " in username:
        return flask.jsonify({"success": False, "error": " app.models.user.Username cannot contain spaces"}), 400

    user.username = username.lower()

    if not create_new and user.protected:
        error_msg = "Cannot change username of protected user"
        return flask.jsonify({"success": False, "error": error_msg}), 400

    requested_group_ids = flask.request.json.get('groups', [])
    if not requested_group_ids:
        return flask.jsonify({"success": False, "error": "Groups are required"}), 400

    new_groups = app.models.user.Group.query.filter(app.models.user.Group.id.in_(requested_group_ids)).all()
    if not new_groups:
        return flask.jsonify({"success": False, "error": "Groups are required"}), 400
    user.groups = new_groups

    auto_start_tide_id = flask.request.json.get('auto_start_tide_id') or None
    user.auto_start_tide_id = auto_start_tide_id

    preferred_language = flask.request.json.get('preferred_language') or None
    user.preferred_language = preferred_language

    if create_new:
        if not flask.request.json.get('password'):
            return flask.jsonify({"success": False, "error": "Password is required"}), 400
        user.password = app.utils.extensions.bcrypt.generate_password_hash(flask.request.json.get('password')).decode('utf-8')
        user.auth_token =  app.routes.auth.generate_auth_token()

    if create_new:
        app.utils.extensions.db.session.add(user)

    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.delete('/user')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_user():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_USERS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    user_id = flask.request.json.get('id')
    user =  app.models.user.User.query.filter_by(id=user_id).first()
    if not user:
        return flask.jsonify({"success": False, "error": " app.models.user.User not found"}), 404

    if user.protected:
        return flask.jsonify({"success": False, "error": "This user is protected. Protected users cannot be deleted."}), 400

    app.utils.extensions.db.session.delete(user)
    app.utils.extensions.db.session.commit()

    instances =  app.models.tide. app.models.tide.TideInstance.query.filter_by(user_id=user_id).all()

    for instance in instances:
        app.utils.extensions.db.session.delete(instance)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.get('/groups')
@app.utils.jwt_validator.jwt_required
def api_admin_groups():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_GROUPS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    groups =  app.models.user.Group.query.order_by(app.models.user.Group.priority).all()

    data = []
    for group in groups:
        data.append({
            "id": group.id,
            "display_name": group.display_name,
            "protected": group.protected,
            "priority": group.priority or 0,
            "settings": group.settings,
            "permissions": {
                "admin_panel": group.perm_admin_panel,
                "view_instances": group.perm_view_instances,
                "edit_instances": group.perm_edit_instances,
                "view_users": group.perm_view_users,
                "edit_users": group.perm_edit_users,
                "view_tides": group.perm_view_tides,
                "edit_tides": group.perm_edit_tides,
                "view_registry": group.perm_view_registry,
                "edit_registry": group.perm_edit_registry,
                "view_groups": group.perm_view_groups,
                "edit_groups": group.perm_edit_groups
            }
        })

    return flask.jsonify({"data": data, "totalRecords": len(data)})

@admin_bp.post('/group')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_group():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_GROUPS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    group_id = flask.request.json.get('id')
    group =  app.models.user.Group.query.filter_by(id=group_id).first()

    create_new = False
    if not group or group_id == "null":
        create_new = True
        group =  app.models.user.Group()
        group.protected = False

    new_display_name = flask.request.json.get('display_name')
    if not new_display_name:
        return flask.jsonify({"success": False, "error": "Display Name is required"}), 400

    group.display_name = new_display_name

    group.perm_admin_panel = flask.request.json.get('perm_admin_panel') or False
    group.perm_view_instances = flask.request.json.get('perm_view_instances') or False
    group.perm_edit_instances = flask.request.json.get('perm_edit_instances') or False
    group.perm_view_users = flask.request.json.get('perm_view_users') or False
    group.perm_edit_users = flask.request.json.get('perm_edit_users') or False
    group.perm_view_tides = flask.request.json.get('perm_view_tides') or False
    group.perm_edit_tides = flask.request.json.get('perm_edit_tides') or False
    group.perm_view_registry = flask.request.json.get('perm_view_registry') or False
    group.perm_edit_registry = flask.request.json.get('perm_edit_registry') or False
    group.perm_view_groups = flask.request.json.get('perm_view_groups') or False
    group.perm_edit_groups = flask.request.json.get('perm_edit_groups') or False

    try:
        group.priority = int(flask.request.json.get('priority') or 0)
    except (TypeError, ValueError):
        group.priority = 0

    group.settings = flask.request.json.get('settings') or {}

    if create_new:
        app.utils.extensions.db.session.add(group)

    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.delete('/group')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_group():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_GROUPS):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    group_id = flask.request.json.get('id')
    group =  app.models.user.Group.query.filter_by(id=group_id).first()
    if not group:
        return flask.jsonify({"success": False, "error": " app.models.user.Group not found."}), 404

    if group.protected:
        return flask.jsonify({"success": False, "error": "This group is protected. Protected groups cannot be deleted."}), 400

    app.utils.extensions.db.session.delete(group)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.get('/registry')
@app.utils.jwt_validator.jwt_required
def api_admin_registry():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_REGISTRY):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    response = {
        "success": True,
        "tidalcase_version": app.__version__,
        "registry": []
    }

    registry = app.models.registry.Registry.query.all()
    for r in registry:
        try:
            #https://registry.kasmweb.com/1.1/list.json
            base_url = r.url.rstrip("/") + "/"
            endpoint = urllib.parse.urljoin(base_url, "list.json")

            resp = requests.get(endpoint, timeout=10)
            resp.raise_for_status()

            raw = resp.json()

            tides = raw.pop('workspaces', [])
            info = raw
        except Exception as e:
            info = {"name": "Failed to get info"}
            tides = []
            app.utils.logger.log("ERROR", f"Failed to get registry info from {r.url}")
        response["registry"].append({
            "id": r.id,
            "url": r.url,
            "info": info,
            "tides": tides
        })

    return flask.jsonify(response)

@admin_bp.post('/registry')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_registry():
    registry_lock = os.environ.get('TIDALCASE_REGISTRY_LOCK')

    if registry_lock:
        return flask.jsonify({"success": False, "error": " app.models.registry.Registry is locked and cannot be modified"}), 403

    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_REGISTRY):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    url = flask.request.json.get('url')
    if not url:
        return flask.jsonify({"success": False, "error": "URL is required"}), 400

    registry =  app.models.registry.Registry.query.filter_by(url=url).first()
    if registry:
        return flask.jsonify({"success": False, "error": " app.models.registry.Registry with this URL already exists"}), 400

    registry =  app.models.registry.Registry(url=url)
    app.utils.extensions.db.session.add(registry)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.delete('/registry')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_registry():
    registry_lock = os.environ.get('TIDALCASE_REGISTRY_LOCK')

    if registry_lock:
        return flask.jsonify({"success": False, "error": " app.models.registry.Registry is locked and cannot be modified"}), 403

    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_REGISTRY):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    registry_id = flask.request.json.get('id')
    registry =  app.models.registry.Registry.query.filter_by(id=registry_id).first()
    if not registry:
        return flask.jsonify({"success": False, "error": " app.models.registry.Registry not found"}), 404

    app.utils.extensions.db.session.delete(registry)
    app.utils.extensions.db.session.commit()

    return flask.jsonify({"success": True})

@admin_bp.get('/logs')
@app.utils.jwt_validator.jwt_required
def api_admin_logs():
    if not flask.g.current_user.has_permission(app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "You do not have permission to view logs"})

    page = flask.request.args.get('page', 1, type=int)
    per_page = flask.request.args.get('per_page', 50, type=int)
    log_type = flask.request.args.get('type', None)

    query =  app.models.log.Log.query

    if log_type and log_type.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        query = query.filter( app.models.log.Log.level == log_type.upper())

    logs_pagination = query.order_by( app.models.log.Log.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = logs_pagination.items

    return flask.jsonify({
        "success": True,
        "logs": [
            {
                "id": log.id,
                "created_at": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "level": log.level,
                "message": log.message
            } for log in logs
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": logs_pagination.total,
            "pages": logs_pagination.pages
        }
    })

@admin_bp.get('/networks')
@app.utils.jwt_validator.jwt_required
def api_admin_networks():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.VIEW_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        all_networks = app.utils.docker.list_available_networks()

        filtered_networks = []
        for network in all_networks:
            network_name = network["name"]
            if (network_name.startswith("lan_") or
                network_name.startswith("vlan_")):
                filtered_networks.append(network)

        return flask.jsonify({"success": True, "networks": filtered_networks})
    except Exception as e:
        app.utils.logger.log("ERROR", f"Error listing networks: {str(e)}")
        return flask.jsonify({"success": False, "error": str(e)}), 500

# ---------------------------------------------------------------------------
#  app.models.agent.Agent management
# ---------------------------------------------------------------------------

def _push_agent_config(agent) -> None:
    """Push current prune config + app image list to the agent."""
    if not agent.api_url or not agent.api_token:
        return
    tides =  app.models.tide.Tide.query.all()
    app_image_set = []
    for d in tides:
        if d.container_docker_image:
            img = d.container_docker_image
            if d.container_docker_registry and "docker.io" not in d.container_docker_registry:
                img = d.container_docker_registry.rstrip("/") + "/" + img
            app_image_set.append(img)
    try:
        flask.requests.post(
            f"{agent.api_url.rstrip('/')}/config",
            json={"prune_mode": agent.prune_mode or 'off', "app_image_set": app_image_set},
            headers={"Authorization": f"Bearer {agent.api_token}"},
            timeout=10,
        )
    except Exception:
        pass


@admin_bp.get('/agents')
@app.utils.jwt_validator.jwt_required
def api_admin_agents():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    agents =  app.models.agent.Agent.query.order_by( app.models.agent.Agent.display_name).all()
    return flask.jsonify({
        "success": True,
        "join_token": app.utils.setup.get_join_token() or '',
        "agents": [
            {
                "id": a.id,
                "display_name": a.display_name,
                "docker_host": a.docker_host,
                "total_cores": a.total_cores,
                "total_memory": a.total_memory,
                "enabled": a.enabled,
                "prune_mode": a.prune_mode or 'off',
                "api_url": a.api_url or '',
                "healthy": a.healthy,
                "last_healthcheck_at": a.last_healthcheck_at.isoformat() if a.last_healthcheck_at else None,
                "created_at": a.created_at,
            }
            for a in agents
        ]
    })

@admin_bp.post('/agent')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_agent():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    agent_id = flask.request.json.get('id')
    agent =  app.models.agent.Agent.query.filter_by(id=agent_id).first() if agent_id else None
    if not agent:
        return flask.jsonify({"success": False, "error": " app.models.agent.Agent not found"}), 404

    display_name = flask.request.json.get('display_name', '').strip()
    if not display_name:
        return flask.jsonify({"success": False, "error": "Display name is required"}), 400

    agent.display_name = display_name
    agent.enabled = bool(flask.request.json.get('enabled', True))

    prune_mode = flask.request.json.get('prune_mode', 'off')
    if prune_mode not in ('off', 'normal', 'aggressive'):
        prune_mode = 'off'
    agent.prune_mode = prune_mode

    try:
        agent.total_cores = float(flask.request.json['total_cores']) if flask.request.json.get('total_cores') else None
    except (ValueError, TypeError):
        return flask.jsonify({"success": False, "error": "total_cores must be a number"}), 400

    try:
        agent.total_memory = int(flask.request.json['total_memory']) if flask.request.json.get('total_memory') else None
    except (ValueError, TypeError):
        return flask.jsonify({"success": False, "error": "total_memory must be an integer"}), 400

    app.utils.extensions.db.session.commit()

    _push_agent_config(agent)

    return flask.jsonify({"success": True, "agent_id": agent.id})

@admin_bp.delete('/agent')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_agent():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    agent_id = flask.request.json.get('id')
    agent =  app.models.agent.Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return flask.jsonify({"success": False, "error": " app.models.agent.Agent not found"}), 404

    running =  app.models.tide. app.models.tide.TideInstance.query.filter_by(agent_id=agent_id).count()
    if running > 0:
        return flask.jsonify({
            "success": False,
            "error": f"Cannot delete agent with {running} running instance(s). Destroy them first."
        }), 400

    app.utils.extensions.db.session.delete(agent)
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})

@admin_bp.post('/agent/test')
@app.utils.jwt_validator.jwt_required
def api_admin_test_agent():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    agent_id = flask.request.json.get('id')
    if agent_id and agent_id != "null":
        agent =  app.models.agent.Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return flask.jsonify({"success": False, "error": " app.models.agent.Agent not found"}), 404

    success, message = app.utils.docker.test_agent_connection(agent)
    return flask.jsonify({"success": success, "message": message})


@admin_bp.post('/agent/<string:agent_id>/healthcheck')
@app.utils.jwt_validator.jwt_required
def api_admin_agent_healthcheck(agent_id: str):
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403
    agent =  app.models.agent.Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return flask.jsonify({"success": False, "error": " app.models.agent.Agent not found"}), 404
    ok, msg = app.utils.docker.test_agent_connection(agent)
    agent.healthy = ok
    agent.last_healthcheck_at = datetime.datetime.now()
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True, "healthy": ok, "message": msg})


# ---------------------------------------------------------------------------
# Storage providers
# ---------------------------------------------------------------------------

@admin_bp.get('/storage-providers')
@app.utils.jwt_validator.jwt_required
def api_admin_storage_providers():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403
    providers = app.models.storage.StorageProvider.query.order_by(app.models.storage.StorageProvider.display_name).all()
    return flask.jsonify({"success": True, "providers": [_storage_provider_dict(p) for p in providers]})


@admin_bp.post('/storage-provider')
@app.utils.jwt_validator.jwt_required
def api_admin_edit_storage_provider():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    body = flask.request.get_json() or {}
    provider_id = body.get('id')
    provider = app.models.storage.StorageProvider.query.filter_by(id=provider_id).first() if provider_id else None
    create_new = provider is None

    if create_new:
        provider = app.models.storage.StorageProvider()

    display_name = (body.get('display_name') or '').strip()
    if not display_name:
        return flask.jsonify({"success": False, "error": "Nome richiesto"}), 400

    provider.display_name = display_name
    provider.enabled = bool(body.get('enabled', True))
    provider.provider_type = body.get('provider_type') or 'rclone'
    provider.default_destination = (body.get('default_destination') or '/storage').strip()

    volume_config = body.get('volume_config')
    if volume_config is not None:
        if isinstance(volume_config, dict):
            provider.volume_config = json.dumps(volume_config)
        else:
            try:
                json.loads(volume_config)
                provider.volume_config = volume_config
            except (ValueError, TypeError):
                return flask.jsonify({"success": False, "error": "volume_config non è JSON valido"}), 400

    if create_new:
        app.utils.extensions.db.session.add(provider)
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True, "id": provider.id})


@admin_bp.delete('/storage-provider')
@app.utils.jwt_validator.jwt_required
def api_admin_delete_storage_provider():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    provider_id = (flask.request.get_json() or {}).get('id')
    provider = app.models.storage.StorageProvider.query.filter_by(id=provider_id).first()
    if not provider:
        return flask.jsonify({"success": False, "error": "Provider non trovato"}), 404

    app.models.storage.TideStorageMount.query.filter_by(storage_provider_id=provider_id).delete()
    app.utils.extensions.db.session.delete(provider)
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@admin_bp.get('/tide/<string:tide_id>/storage-mounts')
@app.utils.jwt_validator.jwt_required
def api_admin_tide_storage_mounts(tide_id: str):
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403
    mounts = app.models.storage.TideStorageMount.query.filter_by(tide_id=tide_id).all()
    return flask.jsonify({"success": True, "mounts": [_storage_mount_dict(m) for m in mounts]})


@admin_bp.post('/tide/<string:tide_id>/storage-mounts')
@app.utils.jwt_validator.jwt_required
def api_admin_save_tide_storage_mounts(tide_id: str):
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    tide = app.models.tide.Tide.query.filter_by(id=tide_id).first()
    if not tide:
        return flask.jsonify({"success": False, "error": "Tide non trovato"}), 404

    body = flask.request.get_json() or {}
    mounts_data = body.get('mounts', [])

    app.models.storage.TideStorageMount.query.filter_by(tide_id=tide_id).delete()
    for m in mounts_data:
        provider_id = m.get('storage_provider_id')
        if not provider_id:
            continue
        mount = app.models.storage.TideStorageMount(
            tide_id=tide_id,
            storage_provider_id=provider_id,
            enabled=bool(m.get('enabled', True)),
            read_only=bool(m.get('read_only', False)),
            destination=(m.get('destination') or '').strip() or None,
        )
        app.utils.extensions.db.session.add(mount)

    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


def _storage_provider_dict(p: app.models.storage.StorageProvider) -> dict:
    return {
        "id": p.id,
        "display_name": p.display_name,
        "enabled": p.enabled,
        "provider_type": p.provider_type,
        "default_destination": p.default_destination,
        "volume_config": p.get_volume_config(),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _storage_mount_dict(m: app.models.storage.TideStorageMount) -> dict:
    provider = app.models.storage.StorageProvider.query.filter_by(id=m.storage_provider_id).first()
    return {
        "id": m.id,
        "storage_provider_id": m.storage_provider_id,
        "provider_display_name": provider.display_name if provider else "?",
        "enabled": m.enabled,
        "read_only": m.read_only,
        "destination": m.destination or "",
    }


# ---------------------------------------------------------------------------
# Tide images
# ---------------------------------------------------------------------------

_TIDE_IMAGES_DIR = os.path.join('data', 'tide_images')
_ALLOWED_IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}


@admin_bp.post('/tide/image')
@app.utils.jwt_validator.jwt_required
def api_admin_upload_tide_image():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.EDIT_TIDES):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    if 'file' not in flask.request.files:
        return flask.jsonify({"success": False, "error": "Nessun file fornito"}), 400

    file = flask.request.files['file']
    if not file.filename:
        return flask.jsonify({"success": False, "error": "Nessun file selezionato"}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_IMAGE_EXTS:
        return flask.jsonify({"success": False, "error": "Tipo file non supportato"}), 400

    filename = f"{uuid.uuid4()}.{ext}"
    os.makedirs(_TIDE_IMAGES_DIR, exist_ok=True)
    file.save(os.path.join(_TIDE_IMAGES_DIR, filename))

    return flask.jsonify({"success": True, "url": f"/api/admin/tide/image/{filename}"})


@admin_bp.get('/tide/image/<string:filename>')
def api_serve_tide_image(filename: str):
    return flask.send_from_directory(os.path.abspath(_TIDE_IMAGES_DIR), filename)
