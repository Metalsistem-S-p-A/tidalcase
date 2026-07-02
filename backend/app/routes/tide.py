import os
import re
import base64
import json
import secrets
import datetime
import tzlocal
import typing
import redis
import traceback
import Crypto.Cipher.AES
import Crypto.Util.Padding
import flask
import app.utils.jwt_validator
import app.models.agent
import app.models.tide
import app.models.user
import app.models.storage
import app.utils.extensions
import app.utils.agent_client
import app.utils.logger
import app.utils.docker

tide_bp = flask.Blueprint('tide', __name__)

_redis: typing.Optional[redis.Redis] = None

def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        url = os.environ.get('CELERY_BROKER_URL', 'redis://tidalcase-redis:6379/0')
        _redis = redis.from_url(url, decode_responses=True)
    return _redis


def _agent_is_alive(agent: app.models.agent.Agent) -> bool:
    """Return True if the agent sent a heartbeat within the last 90 s."""
    if not agent.last_healthcheck_at:
        return False
    return (datetime.datetime.now() - agent.last_healthcheck_at) < datetime.timedelta(seconds=90)


def _parse_mem_bytes(s) -> int:
    """Convert Docker memory string (e.g. '2g', '512m') to bytes."""
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


def _parse_mem_mb(s) -> int:
    return _parse_mem_bytes(s) // (1024 * 1024)


def _agent_free_score(agent: app.models.agent.Agent, tide: app.models.tide.Tide) -> typing.Optional[float]:
    """Return normalised free-resource score (0..2) or None if agent has no capacity."""
    try:
        client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
        info = client.get_info()
    except app.utils.agent_client.AgentError as e:
        app.utils.logger.log("WARNING", f"_agent_free_score: could not reach agent '{agent.display_name}': {e}")
        return None

    total_cores = info.get('total_cores') or agent.total_cores or 4.0
    total_memory = info.get('total_memory_mb') or agent.total_memory or 8192
    avail_memory = info.get('available_memory_mb', 0)
    cpu_pct = info.get('cpu_percent', 0)
    avail_cores = total_cores * max(0.0, 1.0 - cpu_pct / 100.0)

    tide_mem_mb = _parse_mem_mb(tide.container_memory)
    app.utils.logger.log("DEBUG", f"_agent_free_score: agent='{agent.display_name}' avail={avail_cores:.1f}c/{avail_memory}MB cpu={cpu_pct}% tide_needs={tide.container_cores}c/{tide.container_memory}")
    if avail_memory < tide_mem_mb:
        return None
    if avail_cores < (tide.container_cores or 0):
        return None
    return (avail_cores / total_cores) + (avail_memory / total_memory)

def select_agent(tide: app.models.tide.Tide) -> typing.Optional[app.models.agent.Agent]:
    mode = getattr(tide, 'agent_selection_mode', None) or 'auto'
    tide_agent_ids = tide.get_agents()

    if mode == 'fixed':
        agent_id = tide_agent_ids[0] if tide_agent_ids else None
        agent = app.models.agent.Agent.query.get(agent_id) if agent_id else None
        if agent and agent.enabled and _agent_is_alive(agent) and _agent_free_score(agent, tide) is not None:
            return agent
        app.utils.logger.log("WARNING", f"Fixed agent '{agent_id}' unavailable for tide '{tide.display_name}'")
        return None

    all_agents = app.models.agent.Agent.query.filter_by(enabled=True).order_by(app.models.agent.Agent.display_name).all()

    if tide_agent_ids:
        allowed = set(tide_agent_ids)
        all_agents = [a for a in all_agents if a.id in allowed]

    candidates = []
    for agent in all_agents:
        if not _agent_is_alive(agent):
            app.utils.logger.log("WARNING", f"Agent '{agent.display_name}' not alive, skipping")
            continue
        score = _agent_free_score(agent, tide)
        if score is None:
            app.utils.logger.log("WARNING", f"Agent '{agent.display_name}' insufficient resources, skipping")
            continue
        candidates.append((agent, score))

    if not candidates:
        return None

    if mode == 'rr':
        try:
            idx = int(_get_redis().incr(f'tidalcase:rr')) - 1
            return candidates[idx % len(candidates)][0]
        except Exception as e:
            app.utils.logger.log("WARNING", f"RR Redis error, falling back to least-loaded: {e}")

    return max(candidates, key=lambda t: t[1])[0]


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@tide_bp.get('/api/tides')
@app.utils.jwt_validator.jwt_required
def get_tides():
    all_tides = app.models.tide.Tide.query.all()

    user_groups = flask.g.current_user.get_groups()

    is_admin = False
    for group_id in user_groups:
        if group_id == "00000000-0000-0000-0000-000000000000":
            is_admin = True
            break

    visible_tides = []
    for tide in all_tides:
        if is_admin:
            visible_tides.append(tide)
            continue

        tide_groups = []
        if tide.restricted_groups:
            tide_groups = tide.restricted_groups.split(',')

            for group_id in user_groups:
                if group_id in tide_groups:
                    visible_tides.append(tide)
                    break
        else:
            visible_tides.append(tide)

    visible_tides = sorted(visible_tides, key=lambda x: x.display_name)

    response = {
        "success": True,
        "tides": []
    }

    for tide in visible_tides:
        cs = tide.connection_settings or {}
        requires_credentials = (
            tide.tide_type in ('rdp', 'vnc', 'ssh') and
            (not cs.get('username') or not cs.get('password'))
        )
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
            "server_ip": tide.server_ip,
            "server_port": tide.server_port,
            "requires_credentials": requires_credentials,
            "connection_settings": cs
        })

    return flask.jsonify(response)

@tide_bp.get('/api/instances')
@app.utils.jwt_validator.jwt_required
def get_instances():
    instances = app.models.tide.TideInstance.query.filter_by(user_id=flask.g.current_user.id).all()

    response = {
        "success": True,
        "instances": []
    }

    for instance in instances:
        tide = app.models.tide.Tide.query.filter_by(id=instance.tide_id).first()

        vnc_url = instance.direct_url if instance.agent_id else None
        ws_path = f"/desktop/{instance.id}/vnc/websockify"

        response["instances"].append({
            "id": instance.id,
            "session_time_limit": tide.session_time_limit or 0,
            "session_idle_time_limit": tide.session_idle_time_limit or 0,
            "vnc_url": vnc_url,
            "ws_path": ws_path,
            "tide": {
                "id": tide.id,
                "display_name": tide.display_name,
                "description": tide.description,
                "image_path": tide.image_path,
                "tide_type": tide.tide_type,
                "container_docker_image": tide.container_docker_image,
                "container_docker_registry": tide.container_docker_registry,
                "container_cores": tide.container_cores,
                "container_memory": tide.container_memory,
                "server_ip": tide.server_ip,
                "server_port": tide.server_port,
                "open_mode": tide.open_mode,
                "session_time_limit": tide.session_time_limit or 0,
                "session_idle_time_limit": tide.session_idle_time_limit or 0,
            }
        })

    return flask.jsonify(response)

_LOCALE_MAP: dict[str, str] = {
    'it': 'it_IT.UTF-8',
    'en': 'en_US.UTF-8',
}

def _locale_env(lang: str) -> dict:
    locale = _LOCALE_MAP.get(lang, 'en_US.UTF-8')
    return {'LANG': locale, 'LANGUAGE': locale.split('.')[0] + ':' + lang, 'LC_ALL': locale}

def _tz_env() -> dict:
    try:
        tz_name = tzlocal.get_localzone_name()
    except Exception:
        tz_name = 'Etc/UTC'
    
    return {"TZ": tz_name}

def _browser_policy_config_files(user, lang: str = 'en') -> list:
    """Build browser policy config files mounted into every kasm container.

    Firefox always gets a base policy (no ToS modal, no first-run page, no
    crash-restore / reset prompts). If the user's groups define a
    'browser_homepage' setting (highest-priority group wins), the homepage
    is enforced in both Firefox and Chrome/Chromium. Locked, otherwise any
    user_pref baked into the image profile would take precedence.
    """
    url = user.setting_value("browser_homepage")
    url = url.strip() if isinstance(url, str) else None

    firefox_policies = {
        "SkipTermsOfUse": True,
        "OverrideFirstRunPage": "",
        "TranslateEnabled": False,
        "DontCheckDefaultBrowser": True,
        # UI language (matching langpack is baked into the image)
        "RequestedLocales": [lang, "en-US"] if lang != 'en' else ["en-US"],
        "Preferences": {
            "browser.sessionstore.resume_from_crash": {
                "Value": False,
                "Status": "locked",
            },
            # disables the "Open previous tabs?" infobar
            "browser.startup.couldRestoreSession.count": {
                "Value": -1,
                "Status": "locked",
            },
        },
    }
    if url:
        firefox_policies["Homepage"] = {
            "URL": url,
            "StartPage": "homepage",
            "Locked": True,
        }
    firefox_policy = json.dumps({"policies": firefox_policies}, indent=2)

    files = [
        # Firefox: system-wide policies dir + distribution dir of the
        # possible install locations (extra mounts are harmless if absent)
        {"path": "/etc/firefox/policies/policies.json", "content": firefox_policy},
        {"path": "/usr/lib/firefox/distribution/policies.json", "content": firefox_policy},
        {"path": "/usr/lib/firefox-esr/distribution/policies.json", "content": firefox_policy},
        {"path": "/opt/firefox/distribution/policies.json", "content": firefox_policy},
    ]

    if url:
        chrome_policy = json.dumps({
            "HomepageLocation": url,
            "HomepageIsNewTabPage": False,
            "ShowHomeButton": True,
            "RestoreOnStartup": 4,
            "RestoreOnStartupURLs": [url],
        }, indent=2)
        files += [
            # Google Chrome / Chromium managed policy
            {"path": "/etc/opt/chrome/policies/managed/tidalcase-homepage.json", "content": chrome_policy},
            {"path": "/etc/chromium/policies/managed/tidalcase-homepage.json", "content": chrome_policy},
        ]

    return files


def _build_kasmvnc_config(tide: app.models.tide.Tide) -> str:
    idle_min = tide.session_idle_time_limit or 0
    idle_val = str(idle_min * 60) if idle_min > 0 else "never"
    with open(os.path.join(os.path.dirname(__file__), 'kasmvnc_config.yml'), 'r', encoding="utf-8") as f:
        return f.read().replace("{idle_val}", idle_val)


def _request_instance_via_agent(agent, tide: app.models.tide.Tide, lang: str = 'en', credentials: dict | None = None):
    """Handle container creation for tidalcase_agent mode agents."""
    client: app.utils.agent_client.AgentHTTPClient = app.utils.docker.get_agent_client(agent)
    if not client:
        return flask.jsonify({"success": False, "error": "Agent client unavailable"}), 503

    is_guac_tide = tide.tide_type in ["vnc", "rdp", "ssh"]

    image_name = tide.container_docker_image
    if tide.container_docker_registry and "docker.io" not in tide.container_docker_registry:
        image_name = tide.container_docker_registry + "/" + image_name

    instance = app.models.tide.TideInstance(
        tide_id=tide.id,
        user_id=flask.g.current_user.id,
        agent_id=agent.id,
        vnc_password=secrets.token_hex(8),
    )
    app.utils.extensions.db.session.add(instance)
    app.utils.extensions.db.session.commit()

    name = f'tidalcase-{instance.id}'

    mounts = []
    if not is_guac_tide:
        storage_mounts = app.models.storage.TideStorageMount.query.filter_by(
            tide_id=tide.id, enabled=True
        ).all()
        for sm in storage_mounts:
            provider = app.models.storage.StorageProvider.query.filter_by(
                id=sm.storage_provider_id, enabled=True
            ).first()
            if not provider:
                continue
            vol_config = provider.get_volume_config()
            driver = vol_config.get('driver', 'local')
            driver_opts = vol_config.get('driver_opts', {})
            vol_name = re.sub(r'[^a-zA-Z0-9._-]', '_', f"tidalcase-storage-{provider.id}_{flask.g.current_user.id}")
            try:
                client.ensure_volume(vol_name, driver=driver, driver_opts=driver_opts)
            except app.utils.agent_client.AgentError as e:
                app.utils.logger.log("ERROR", f"Storage volume error for provider '{provider.display_name}': {e}")
                app.utils.extensions.db.session.delete(instance)
                app.utils.extensions.db.session.commit()
                return flask.jsonify({"success": False, "error": f"Errore volume storage '{provider.display_name}': {e}"}), 500
            target = sm.destination or provider.default_destination
            mounts.append({"type": "volume", "source": vol_name, "target": target, "mode": "ro" if sm.read_only else "rw"})

    session_limit_s = (tide.session_time_limit or 0) * 60

    try:
        if is_guac_tide:
            result = client.run_container(
                image=image_name,
                name=name,
                env={"GUAC_KEY": flask.g.current_user.auth_token[:32]},
                mem_limit="512m",
                cpu_shares=512,
                session_time_limit_s=session_limit_s or None,
            )
            # Re-fetch: check_containers may have deleted the instance if the
            # container exited during the run_container wait (race condition).
            live = app.models.tide.TideInstance.query.filter_by(id=instance.id).first()
            if not live:
                return flask.jsonify({"success": False, "error": "Container exited during startup"}), 500
            live.direct_url = result.get('guac_url')
            live.guac_token = generate_guac_token(tide, flask.g.current_user, credentials or {})
            app.utils.extensions.db.session.commit()
        else:
            vnc_user = tide.vnc_user or "kasm_user"
            auth_header = base64.b64encode(f"{vnc_user}:{instance.vnc_password}".encode()).decode()
            result = client.run_container(
                image=image_name,
                name=name,
                env={"DISPLAY": ":1", "VNC_PW": instance.vnc_password, "VNC_USER": vnc_user, **_locale_env(lang), **_tz_env()},
                mem_limit=tide.container_memory,
                memswap_limit=tide.container_swap,
                cpu_shares=int(tide.container_cores * 1024),
                mounts=mounts,
                config_files=[{
                    "path": "/etc/kasmvnc/kasmvnc.yaml",
                    "content": _build_kasmvnc_config(tide),
                }] + _browser_policy_config_files(flask.g.current_user, lang),
                auth_header=auth_header,
                session_time_limit_s=session_limit_s or None,
            )
            live = app.models.tide.TideInstance.query.filter_by(id=instance.id).first()
            if not live:
                return flask.jsonify({"success": False, "error": "Container exited during startup"}), 500
            live.direct_url = result.get('vnc_url')
            app.utils.extensions.db.session.commit()
    except app.utils.agent_client.AgentPullingError:
        app.utils.extensions.db.session.delete(instance)
        app.utils.extensions.db.session.commit()
        return flask.jsonify({
            "success": False,
            "pulling": True,
            "error": "Image pull in progress on agent, please retry in a moment.",
            "agent_id": str(agent.id),
            "image": image_name,
        }), 202
    except app.utils.agent_client.AgentError as e:
        app.utils.logger.log("ERROR", f"Agent container error: {e}")
        try:
            client.remove_container(name)
        except Exception:
            pass
        app.utils.extensions.db.session.delete(instance)
        app.utils.extensions.db.session.commit()
        return flask.jsonify({"success": False, "error": f"Agent error: {e}"}), 500

    return flask.jsonify({"success": True, "instance_id": live.id, "open_mode": tide.open_mode})


@tide_bp.get('/api/pull-status')
@app.utils.jwt_validator.jwt_required
def pull_status():
    agent_id = flask.request.args.get('agent_id', '')
    image = flask.request.args.get('image', '')
    if not agent_id or not image:
        return flask.jsonify({"success": False, "status": "unknown"}), 400
    agent = app.models.agent.Agent.query.filter_by(id=agent_id, enabled=True).first()
    if not agent:
        return flask.jsonify({"success": False, "status": "unknown"}), 404
    client = app.utils.docker.get_agent_client(agent)
    if not client:
        return flask.jsonify({"success": True, "status": "unknown"})
    result = client.get_pull_status(image)
    return flask.jsonify({
        "success": True,
        "status": result.get("status", "unknown"),
        "percent": result.get("percent", 0),
        "layers_done": result.get("layers_done", 0),
        "layers_total": result.get("layers_total", 0),
        "error": result.get("error"),
    })


@tide_bp.post('/api/instance/request')
@app.utils.jwt_validator.jwt_required
def request_new_instance():
    tide_id = flask.request.json.get('tide_id')
    tide = app.models.tide.Tide.query.filter_by(id=tide_id).first()
    if not tide:
        return flask.jsonify({"success": False, "error": "Tide not found"}), 404

    user_groups = flask.g.current_user.get_groups()

    is_admin = False
    for group_id in user_groups:
        if group_id == "00000000-0000-0000-0000-000000000000":
            is_admin = True
            break

    if not is_admin:
        tide_groups = []
        if tide.restricted_groups:
            tide_groups = tide.restricted_groups.split(',')

            has_access = False
            for group_id in user_groups:
                if group_id in tide_groups:
                    has_access = True
                    break
        else:
            has_access = True

        if not has_access:
            return flask.jsonify({"success": False, "error": "You don't have access to this tide"}), 403

    session_limit = flask.g.current_user.setting_value("max_sessions_per_user") or 0
    if session_limit > 0:
        active_count = app.models.tide.TideInstance.query.filter_by(user_id=flask.g.current_user.id).count()
        if active_count >= session_limit:
            return flask.jsonify({"success": False, "error": f"Limite sessioni raggiunto ({session_limit} max)"}), 429

    agent = select_agent(tide)
    if agent is None:
        return flask.jsonify({"success": False, "error": "No agents available. Deploy at least one agent and ensure it is connected."}), 503

    lang = flask.request.json.get('language', 'en')
    credentials = flask.request.json.get('credentials')
    return _request_instance_via_agent(agent, tide, lang, credentials=credentials)


def _encrypt_token(token, auth_token):
        iv = os.urandom(16)
        auth_token = auth_token[:32]
        cipher = Crypto.Cipher.AES.new(auth_token, Crypto.Cipher.AES.MODE_CBC, iv)

        padded_data = Crypto.Util.Padding.pad(json.dumps(token).encode(), Crypto.Cipher.AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)

        data = {
            'iv': base64.b64encode(iv).decode('utf-8'),
            'value': base64.b64encode(encrypted_data).decode('utf-8')
        }

        json_data = json.dumps(data)
        return base64.b64encode(json_data.encode()).decode('utf-8')

def generate_guac_token(tide: app.models.tide.Tide, user: app.models.user.User, extra_credentials: dict) -> str:
    settings = {
        "hostname": tide.server_ip,
        "port": tide.server_port,
        **(tide.connection_settings or {}),
    }
    if extra_credentials:
        settings.update({k: v for k, v in extra_credentials.items() if v})
    guac_token = {
        "connection": {
            "type": tide.tide_type,
            "settings": settings,
        },
    }
    return _encrypt_token(guac_token, user.auth_token.encode())

@tide_bp.get('/api/tide/<string:instance_id>/info')
@app.utils.jwt_validator.jwt_required
def tide_info(instance_id: str):
    instance = app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        return flask.jsonify({"success": False, "error": "Instance not found"}), 404

    if instance.user_id == flask.g.current_user.id:
        pass
    else:
        user_groups = flask.g.current_user.get_groups()
        is_admin = False
        for group_id in user_groups:
            if group_id == "00000000-0000-0000-0000-000000000000":
                is_admin = True
                break

        if not is_admin:
            return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    tide_obj = app.models.tide.Tide.query.filter_by(id=instance.tide_id).first()
    using_guac = tide_obj.tide_type in ["vnc", "rdp", "ssh"]
    guac_token = None
    if using_guac:
        guac_token = instance.guac_token
        if not guac_token:
            return flask.jsonify({"success": False, "error": "Credentials required but not provided"}), 400
            

    return flask.jsonify({
        "success": True,
        "instance_id": instance_id,
        "tide": {
            "id": tide_obj.id,
            "display_name": tide_obj.display_name,
            "tide_type": tide_obj.tide_type,
        },
        "guacamole": using_guac,
        "guac_token": guac_token,
        "session_time_limit": tide_obj.session_time_limit or 0,
        "session_idle_time_limit": tide_obj.session_idle_time_limit or 0,
        "instance_created_at": int(instance.created_at.timestamp() * 1000),
        "vnc_url": instance.direct_url
    })


def _destroy_instance(instance: app.models.tide.TideInstance, remove_container: bool = True) -> None:
    """Delete the DB record and optionally tell the agent to remove the container."""
    caller = ''.join(traceback.format_stack(limit=4)[:-1])
    app.utils.logger.log("INFO", f"_destroy_instance called for '{instance.id}' remove_container={remove_container} from:\n{caller}")
    if remove_container:
        agent = app.models.agent.Agent.query.filter_by(id=instance.agent_id).first()
        if agent:
            client = app.utils.docker.get_agent_client(agent)
            if client:
                try:
                    client.remove_container(f'tidalcase-{instance.id}')
                except Exception:
                    pass
    app.utils.extensions.db.session.delete(instance)
    app.utils.extensions.db.session.commit()


@tide_bp.get('/api/instance/<string:instance_id>/destroy')
@app.utils.jwt_validator.jwt_required
def stop_instance(instance_id: str):
    instance: app.models.tide.TideInstance = app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        return flask.jsonify({"success": False, "error": "Instance not found"}), 404

    if instance.user_id != flask.g.current_user.id:
        user_groups = flask.g.current_user.get_groups()
        is_admin = any(g == "00000000-0000-0000-0000-000000000000" for g in user_groups)
        if not is_admin:
            return flask.jsonify({"success": False, "error": "Unauthorized"}), 403

    _destroy_instance(instance)
    return flask.jsonify({"success": True})


# ---------------------------------------------------------------------------
# File transfer helpers
# ---------------------------------------------------------------------------

def _get_owned_instance(instance_id: str) -> typing.Optional[app.models.tide.TideInstance]:
    instance = app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        return None
    if instance.user_id == flask.g.current_user.id:
        return instance
    for gid in flask.g.current_user.get_groups():
        if gid == "00000000-0000-0000-0000-000000000000":
            return instance
    return None


@tide_bp.get('/api/instance/<string:instance_id>/files/downloads')
@app.utils.jwt_validator.jwt_required
def list_instance_downloads(instance_id: str):
    instance = _get_owned_instance(instance_id)
    if instance is None:
        return flask.jsonify({'success': False, 'error': 'not found'}), 404

    agent = app.models.agent.Agent.query.get(instance.agent_id)
    if not agent:
        return flask.jsonify({'success': False, 'error': 'agent not found'}), 404

    tide = app.models.tide.Tide.query.get(instance.tide_id)

    client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
    name = f'tidalcase-{instance.id}'
    try:
        files = client.list_downloads(name, tide.download_path)
        return flask.jsonify({'success': True, 'files': files})
    except app.utils.agent_client.AgentError as e:
        return flask.jsonify({'success': False, 'error': str(e)}), 502


@tide_bp.get('/api/instance/<string:instance_id>/files/downloads/<string:filename>')
@app.utils.jwt_validator.jwt_required
def download_instance_file(instance_id: str, filename: str):
    if '..' in filename or filename.startswith('/'):
        flask.abort(400)

    instance = _get_owned_instance(instance_id)
    if instance is None:
        flask.abort(404)

    agent = app.models.agent.Agent.query.get(instance.agent_id)
    if not agent:
        flask.abort(404)

    tide = app.models.tide.Tide.query.get(instance.tide_id)
    client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
    name = f'tidalcase-{instance.id}'
    try:
        resp = client.get_download_stream(name, filename, tide.download_path)
    except app.utils.agent_client.AgentError:
        flask.abort(502)

    if resp.status_code != 200:
        flask.abort(resp.status_code)

    return flask.Response(
        flask.stream_with_context(resp.iter_content(65536)),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/octet-stream',
        }
    )


@tide_bp.post('/api/instance/<string:instance_id>/files/uploads')
@app.utils.jwt_validator.jwt_required
def upload_instance_file(instance_id: str):
    instance = _get_owned_instance(instance_id)
    if instance is None:
        return flask.jsonify({'success': False, 'error': 'not found'}), 404

    incoming = flask.request.files.getlist('file[]')
    if not incoming:
        return flask.jsonify({'success': False, 'error': 'no files'}), 400

    agent = app.models.agent.Agent.query.get(instance.agent_id)
    if not agent:
        return flask.jsonify({'success': False, 'error': 'agent not found'}), 404

    file_pairs = []
    for f in incoming:
        safe_name = os.path.basename(f.filename or '')
        if safe_name and '..' not in safe_name:
            file_pairs.append((safe_name, f.read()))

    if not file_pairs:
        return flask.jsonify({'success': False, 'error': 'no valid files'}), 400

    tide = app.models.tide.Tide.query.get(instance.tide_id)
    client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
    container_name = f'tidalcase-{instance.id}'
    try:
        names = client.upload_files(container_name, file_pairs, tide.upload_path)
        return flask.jsonify({'success': True, 'names': names})
    except app.utils.agent_client.AgentError as e:
        return flask.jsonify({'success': False, 'error': str(e)}), 502

@tide_bp.get('/api/tide/<string:instance_id>/exists')
@app.utils.jwt_validator.jwt_required
def instance_check(instance_id: str):
    instance = app.models.tide.TideInstance.query.filter_by(id=instance_id).first()
    if not instance:
        return flask.jsonify({"exists": False}), 200

    if instance.user_id == flask.g.current_user.id:
        pass
    else:
        user_groups = flask.g.current_user.get_groups()
        is_admin = False
        for group_id in user_groups:
            if group_id == "00000000-0000-0000-0000-000000000000":
                is_admin = True
                break

        if not is_admin:
            return flask.jsonify({"exists": False}), 200

    agent = app.models.agent.Agent.query.get(instance.agent_id)
    if agent:
        client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
        try:
            client.instance_check(f'tidalcase-{instance.id}')
        except app.utils.agent_client.AgentError:
            return flask.jsonify({'exists': False}), 200
    return flask.jsonify({'exists': True}), 200