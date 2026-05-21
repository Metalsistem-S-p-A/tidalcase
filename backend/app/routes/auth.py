import json
import random
import ssl
import string
import os
import urllib.parse
import datetime
import jwt as pyjwt
import pyotp
import requests
import flask
import sqlalchemy
import ldap3
import app.utils.permissions
import app.utils.extensions
import app.utils.jwt_validator
import app.models.user
import app.models.auth_provider

auth_bp = flask.Blueprint('auth', __name__)

JWT_EXPIRY_HOURS = 24
REFRESH_TOKEN_EXPIRY_DAYS = 30

def _build_user_permissions(user_id):
    """Build permissions dict and isAdmin flag for JWT payload."""
    is_admin = app.utils.permissions.Permissions.check_permission(user_id, app.utils.permissions.Permissions.ADMIN_PANEL)
    resources = [
        ("instances", app.utils.permissions.Permissions.VIEW_INSTANCES, app.utils.permissions.Permissions.EDIT_INSTANCES),
        ("tides",     app.utils.permissions.Permissions.VIEW_TIDES,      app.utils.permissions.Permissions.EDIT_TIDES),
        ("users",     app.utils.permissions.Permissions.VIEW_USERS,     app.utils.permissions.Permissions.EDIT_USERS),
        ("registry",  app.utils.permissions.Permissions.VIEW_REGISTRY,  app.utils.permissions.Permissions.EDIT_REGISTRY),
        ("groups",    app.utils.permissions.Permissions.VIEW_GROUPS,    app.utils.permissions.Permissions.EDIT_GROUPS),
    ]
    permissions = {}
    for resource, view_perm, edit_perm in resources:
        if app.utils.permissions.Permissions.check_permission(user_id, edit_perm):
            permissions[resource] = "write"
        elif app.utils.permissions.Permissions.check_permission(user_id, view_perm):
            permissions[resource] = "read"
        else:
            permissions[resource] = "none"
    return is_admin, permissions

def _jwt_response(data: dict, token: str):
    """Return a JSON response that also sets the access_token cookie for nginx auth_request."""
    resp = flask.make_response(flask.jsonify(data))
    resp.set_cookie(
        'access_token', token,
        httponly=True,
        samesite='Lax',
        max_age=JWT_EXPIRY_HOURS * 3600,
        path='/',
    )
    return resp

def _generate_jwt(user, auth_provider='local', auth_provider_name=None):
    """Generate a signed JWT for the given user."""
    secret = os.environ.get('SECRET_KEY', 'devsecret')
    is_admin, permissions = _build_user_permissions(user.id)
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "userId": str(user.id),
        "username": user.username,
        "authProvider": auth_provider,
        "authProviderName": auth_provider_name,
        "isAdmin": is_admin,
        "permissions": permissions,
        "settings": user.get_settings(),
        "preferred_language": user.preferred_language,
        "iat": now,
        "exp": now + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _full_jwt_response(user, auth_provider='local', auth_provider_name=None, remember_me=True, auth_provider_id=None):
    token = _generate_jwt(user, auth_provider, auth_provider_name)
    is_admin, permissions = _build_user_permissions(user.id)
    resp = _jwt_response({
        "token": token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "authProvider": auth_provider,
            "authProviderName": auth_provider_name,
            "isAdmin": is_admin,
            "permissions": permissions,
            "settings": user.get_settings()
        },
    }, token)
    if remember_me:
        _attach_refresh_token(resp, user, auth_provider_id)
    return resp


def _attach_refresh_token(response, user, auth_provider_id=None):
    """Generate a refresh token, store it in DB, and attach it as httpOnly cookie."""
    token_value = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
    rt = app.models.user.RefreshToken(
        user_id=str(user.id),
        token=token_value,
        expires_at=expires_at,
        auth_provider_id=auth_provider_id,
    )
    app.utils.extensions.db.session.add(rt)
    app.utils.extensions.db.session.commit()
    response.set_cookie(
        'refresh_token', token_value,
        httponly=True, samesite='Lax',
        max_age=REFRESH_TOKEN_EXPIRY_DAYS * 24 * 3600,
        path='/',
    )


def _get_device_name(request) -> str:
    ua = request.headers.get('User-Agent', '')
    if 'Mobile' in ua or 'Android' in ua or 'iPhone' in ua:
        return 'Mobile Browser'
    for browser in ('Edg', 'Chrome', 'Firefox', 'Safari'):
        if browser in ua:
            return browser
    return 'Browser'


def _handle_post_auth(user, auth_provider, auth_provider_name, device_id, remember_me=False, auth_provider_id=None):
    if user.mfa_enabled:
        if device_id:
            now = datetime.datetime.now(datetime.timezone.utc)
            trusted = app.models.user.TrustedDevice.query.filter_by(
                id=device_id, user_id=str(user.id)
            ).filter(app.models.user.TrustedDevice.expires_at > now).first()
            if trusted:
                trusted.last_used_at = now
                app.utils.extensions.db.session.commit()
                return _full_jwt_response(user, auth_provider, auth_provider_name, remember_me, auth_provider_id)

        secret = os.environ.get('SECRET_KEY', 'devsecret')
        pending_payload = {
            "userId": str(user.id),
            "authProvider": auth_provider,
            "authProviderName": auth_provider_name,
            "authProviderId": str(auth_provider_id) if auth_provider_id else None,
            "mfaPending": True,
            "remember_me": remember_me,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
        }
        pending_token = pyjwt.encode(pending_payload, secret, algorithm="HS256")
        return flask.jsonify({
            "requiresMfa": True,
            "tempUserId": pending_token,
            "username": user.username,
        })

    return _full_jwt_response(user, auth_provider, auth_provider_name, remember_me, auth_provider_id)


def _ldap_authenticate(settings: dict, username: str, password: str):
    """Attempt LDAP authentication against a provider's settings.
    Returns (user_dn, user_email) on success, (None, None) on failure.
    """

    ldap_cfg = settings.get('ldap', {})
    server_urls = [s for s in (ldap_cfg.get('servers') or []) if s]
    if not server_urls:
        return None, None

    search_filter = (ldap_cfg.get('searchFilter') or '(uid={{username}})').replace('{{username}}', username)
    # LDAP filters must be wrapped in parentheses; auto-correct if missing
    if search_filter and not search_filter.startswith('('):
        search_filter = f'({search_filter})'
    search_base   = ldap_cfg.get('searchBase') or ''
    bind_dn       = ldap_cfg.get('bindDN') or ''
    bind_creds    = ldap_cfg.get('bindCredentials') or ''
    email_field   = ldap_cfg.get('emailField') or 'mail'
    tls_reject    = ldap_cfg.get('tlsRejectUnauthorized', True)
    tls_ca_cert   = (ldap_cfg.get('tlsCaCert') or '').strip()

    tls = None
    if tls_ca_cert:
        tls = ldap3.Tls(validate=ssl.CERT_REQUIRED if tls_reject else ssl.CERT_NONE, ca_certs_data=tls_ca_cert)
    elif not tls_reject:
        tls = ldap3.Tls(validate=ssl.CERT_NONE)

    for url in server_urls:
        try:
            use_ssl = url.lower().startswith('ldaps://')
            server = ldap3.Server(url, use_ssl=use_ssl, tls=tls if use_ssl else None, get_info=None)

            # Bind with the service account to find the user
            conn = ldap3.Connection(server, user=bind_dn or None, password=bind_creds or None, auto_bind=True)
            conn.search(search_base, search_filter, attributes=[email_field])

            if not conn.entries:
                conn.unbind()
                app.utils.logger.log("INFO", f"LDAP: user '{username}' not found via {url}")
                continue

            user_dn = conn.entries[0].entry_dn
            user_email = None
            try:
                if email_field in conn.entries[0]:
                    user_email = str(conn.entries[0][email_field])
            except Exception:
                pass
            conn.unbind()

            # Verify the user's password
            user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
            user_conn.unbind()
            app.utils.logger.log("INFO", f"LDAP: authenticated '{username}' via {url}")
            return user_dn, user_email

        except ldap3.core.exceptions.LDAPBindError:
            app.utils.logger.log("WARNING", f"LDAP: invalid credentials for '{username}' on {url}")
            return None, None
        except Exception as e:
            app.utils.logger.log("ERROR", f"LDAP: error on {url}: {e}")
            continue

    return None, None

@auth_bp.get('/api/auth/providers/enabled')
def get_enabled_providers():
    """Return the list of enabled auth providers for the login page."""
    try:
        providers = app.models.auth_provider.AuthProvider.query.filter_by(enabled=True).order_by(app.models.auth_provider.AuthProvider.priority.asc()).all()
        if providers:
            return flask.jsonify([p.to_dict() for p in providers])
    except Exception:
        pass
    # Fallback: always expose local login
    return flask.jsonify([{
        "_id": "local",
        "name": "Local",
        "type": "local",
        "slug": "local",
        "priority": 0,
        "enabled": True,
    }])

@auth_bp.before_app_request
def before_request():
    if os.environ.get('TIDALCASE_TRAEFIK_AUTHENTIK') != '1':
        return
    if flask.request.endpoint and flask.request.endpoint in [
        'auth.login', 'auth.logout', 'auth.get_enabled_providers', 'auth.me', 'auth.tide_connect'
    ]:
        return
    try:
        check_external_identity()
    except Exception as e:
        app.utils.logger.log("ERROR", f"before_request external identity: {e}")

@auth_bp.get('/api/auth/me')
def me():
    """Return current user info by validating the access_token cookie directly."""
    token = flask.request.cookies.get('access_token', '')
    if not token:
        return flask.jsonify({"message": "auth.loginFailed"}), 401
    try:
        secret = os.environ.get('SECRET_KEY', 'devsecret')
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        user_id = payload.get('userId')
        if not user_id:
            return flask.jsonify({"message": "auth.loginFailed"}), 401
        user = app.utils.extensions.db.session.get(app.models.user.User, user_id)
        if not user:
            return flask.jsonify({"message": "auth.loginFailed"}), 401
    except pyjwt.ExpiredSignatureError:
        return flask.jsonify({"message": "auth.sessionExpired"}), 401
    except pyjwt.InvalidTokenError:
        return flask.jsonify({"message": "auth.loginFailed"}), 401
    is_admin, permissions = _build_user_permissions(user.id)
    return flask.jsonify({
        "user": {
            "id": str(user.id),
            "username": user.username,
            "authProvider": payload.get('authProvider', 'local'),
            "authProviderName": payload.get('authProviderName'),
            "isAdmin": is_admin,
            "permissions": permissions,
            "settings": user.get_settings(),
        }
    })


def user_exists(username):
    """Check if a user exists"""
    return app.models.user.User.query.filter(sqlalchemy.sql.func.lower(app.models.user.User.username) == sqlalchemy.sql.func.lower(username)).first() is not None

def create_external_user(username):
    """Create a user with a random password and no group membership"""
    # Generate a random password
    random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))

    # Get the unassigned group
    unassigned_group = app.models.user.Group.query.filter_by(display_name="Unassigned").first()
    group_id = f"{unassigned_group.id}" if unassigned_group else ""

    # Create the user with lowercase username
    user = create_user(username, random_password, '', [group_id] if group_id else [], usertype="External")

    app.utils.logger.log("INFO", f"Created external user {username} with random password")
    return user

def check_external_identity():
    """Check if external identity is enabled and log in the user if it is"""
    ext_identity = None
    auth_method = "unknown"

    # Check if Traefik + Authentik header-based authentication is enabled
    if os.environ.get('TIDALCASE_TRAEFIK_AUTHENTIK') == '1':
        # Priority: Header-based authentication via Traefik + Authentik
        authentik_username = flask.request.headers.get('X-Authentik-Username')
        if authentik_username and authentik_username.strip():
            ext_identity = authentik_username.strip()
            auth_method = "Traefik + Authentik header"
            app.utils.logger.log("INFO", f"Using Traefik + Authentik header authentication for user: {ext_identity}")
        else:
            app.utils.logger.log("WARNING", "TIDALCASE_TRAEFIK_AUTHENTIK is enabled but X-Authentik-Username header is missing or empty")
            # Fall back to environment variable method
            ext_identity = os.environ.get('TIDALCASE_EXT_USER')
            if ext_identity:
                auth_method = "environment variable (fallback)"
                app.utils.logger.log("INFO", f"Falling back to environment variable authentication for user: {ext_identity}")
    else:
        # Default: Environment variable method
        ext_identity = os.environ.get('TIDALCASE_EXT_USER')
        if ext_identity:
            auth_method = "environment variable"
            app.utils.logger.log("INFO", f"Using environment variable authentication for user: {ext_identity}")

    if ext_identity:
        try:
            user = app.models.user.User.query.filter(sqlalchemy.sql.func.lower(app.models.user.User.username) == sqlalchemy.sql.func.lower(ext_identity)).first()
            if not user:
                user = create_external_user(ext_identity)
            flask.g.current_user = user
            app.utils.logger.log("INFO", f"External identity set via {auth_method}: {user.username}")
            return True
        except Exception as e:
            app.utils.logger.log("ERROR", f"External identity failed for {ext_identity}: {e}")
            return False

    return False

@auth_bp.post('/api/auth/login')
def login():
    """JWT-based login used by the Angular frontend."""
    data = flask.request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    device_id = (data.get('deviceId') or '').strip()
    remember_me = bool(data.get('remember_me', False))

    if not username or not password:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    # 1. Local authentication
    user = app.models.user.User.query.filter(sqlalchemy.sql.func.lower(app.models.user.User.username) == sqlalchemy.sql.func.lower(username)).first()
    if user and user.usertype != 'External' and app.utils.extensions.bcrypt.check_password_hash(user.password, password):
        return _handle_post_auth(user, 'local', None, device_id, remember_me)

    # 2. LDAP authentication — try each enabled LDAP provider in priority order
    try:
        ldap_providers = app.models.auth_provider.AuthProvider.query.filter_by(type='ldap', enabled=True).order_by(app.models.auth_provider.AuthProvider.priority.asc()).all()
    except Exception as e:
        app.utils.logger.log("ERROR", str(e))
        ldap_providers = []

    for provider in ldap_providers:
        settings = provider.settings or {}

        user_dn, user_email = _ldap_authenticate(settings, username, password)
        if user_dn is None:
            continue

        # Find or create the local DB record for this LDAP user
        db_user = app.models.user.User.query.filter(sqlalchemy.sql.func.lower(app.models.user.User.username) == sqlalchemy.sql.func.lower(username)).first()
        if not db_user:
            unassigned = app.models.user.Group.query.filter_by(display_name="Unassigned").first()
            random_pw = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
            db_user = create_user(username.lower(), user_email.lower(), random_pw, str(unassigned.id) if unassigned else '', usertype='External')

        return _handle_post_auth(db_user, 'ldap', provider.name, device_id, remember_me, provider.id)

    return flask.jsonify({"message": "auth.loginFailed"}), 401


@auth_bp.post('/api/auth/verify-mfa')
def verify_mfa():
    data = flask.request.get_json() or {}
    temp_user_id = data.get('tempUserId', '')
    token = (data.get('token') or '').strip()
    trust_device = bool(data.get('trustDevice', False))
    device_id = (data.get('deviceId') or '').strip()

    try:
        secret = os.environ.get('SECRET_KEY', 'devsecret')
        payload = pyjwt.decode(temp_user_id, secret, algorithms=["HS256"])
        if not payload.get('mfaPending'):
            return flask.jsonify({"message": "auth.loginFailed"}), 401
        user_id = payload.get('userId')
        auth_provider = payload.get('authProvider', 'local')
        auth_provider_name = payload.get('authProviderName')
        auth_provider_id = payload.get('authProviderId')
        remember_me = bool(payload.get('remember_me', False))
    except pyjwt.InvalidTokenError:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    user = app.utils.extensions.db.session.get(app.models.user.User, user_id)
    if not user or not user.mfa_secret:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(token, valid_window=2):
        return flask.jsonify({"message": "mfa.errors.invalid"}), 400

    jwt_token = _generate_jwt(user, auth_provider, auth_provider_name)
    is_admin, permissions = _build_user_permissions(user.id)
    response_data = {
        "token": jwt_token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "authProvider": auth_provider,
            "authProviderName": auth_provider_name,
            "isAdmin": is_admin,
            "permissions": permissions,
            "settings": user.get_settings(),
        }
    }

    if trust_device:
        now = datetime.datetime.now(datetime.timezone.utc)
        duration = user.mfa_trust_duration or 30
        expires = now + datetime.timedelta(days=duration)
        trusted = None
        if device_id:
            trusted = app.models.user.TrustedDevice.query.filter_by(id=device_id, user_id=str(user.id)).first()
        if trusted:
            trusted.last_used_at = now
            trusted.expires_at = expires
        else:
            trusted = app.models.user.TrustedDevice(
                user_id=str(user.id),
                device_name=_get_device_name(flask.request),
                ip_address=flask.request.remote_addr,
                expires_at=expires,
            )
            app.utils.extensions.db.session.add(trusted)
        app.utils.extensions.db.session.commit()
        response_data['deviceId'] = str(trusted.id)

    resp = _jwt_response(response_data, jwt_token)
    _attach_refresh_token(resp, user, auth_provider_id)
    return resp


@auth_bp.post('/api/auth/refresh')
def refresh():
    """Issue a new JWT using a valid refresh token cookie."""
    rt_value = flask.request.cookies.get('refresh_token')
    if not rt_value:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    now = datetime.datetime.now(datetime.timezone.utc)
    rt = app.models.user.RefreshToken.query.filter_by(token=rt_value).filter(
        app.models.user.RefreshToken.expires_at > now
    ).first()
    if not rt:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    user = app.utils.extensions.db.session.get(app.models.user.User, rt.user_id)
    if not user:
        return flask.jsonify({"message": "auth.loginFailed"}), 401

    if rt.auth_provider_id:
        provider = app.utils.extensions.db.session.get(app.models.auth_provider.AuthProvider, rt.auth_provider_id)
        auth_provider = provider.type if provider else 'local'
        auth_provider_name = provider.name if provider else None
    else:
        auth_provider = 'local'
        auth_provider_name = None

    # Rotate the refresh token
    new_token_value = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))
    rt.token = new_token_value
    rt.expires_at = now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
    app.utils.extensions.db.session.commit()

    resp = _full_jwt_response(user, auth_provider, auth_provider_name, remember_me=False)
    resp.set_cookie(
        'refresh_token', new_token_value,
        httponly=True, samesite='Lax',
        max_age=REFRESH_TOKEN_EXPIRY_DAYS * 24 * 3600,
        path='/',
    )
    return resp


@auth_bp.post('/api/auth/logout')
def logout():
    rt_value = flask.request.cookies.get('refresh_token')
    if rt_value:
        rt = app.models.user.RefreshToken.query.filter_by(token=rt_value).first()
        if rt:
            app.utils.extensions.db.session.delete(rt)
            app.utils.extensions.db.session.commit()

    if os.environ.get('TIDALCASE_TRAEFIK_AUTHENTIK') == '1':
        hostname = flask.request.host.split(':')[0]
        authentik_logout_url = f"https://authentik.{hostname}/flows/-/default/invalidation/"
        response = flask.make_response({"success": True, "redirect": authentik_logout_url})
    else:
        response = flask.make_response({"success": True})

    response.set_cookie('access_token', '', expires=0, path='/')
    response.set_cookie('refresh_token', '', expires=0, path='/')
    return response


@auth_bp.patch('/api/user/language')
@app.utils.jwt_validator.jwt_required
def update_language():
    lang = (flask.request.get_json() or {}).get('language', 'system')
    if lang not in ('en', 'it', 'system'):
        return flask.jsonify({"success": False, "error": "invalid language"}), 400
    flask.g.current_user.preferred_language = lang
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})

@auth_bp.get('/tide_connect')
def tide_connect():
    """nginx auth_request endpoint: validates access_token cookie or Authentik header."""
    # Authentik SSO: header set by Traefik
    if os.environ.get('TIDALCASE_TRAEFIK_AUTHENTIK') == '1':
        username = flask.request.headers.get('X-Authentik-Username', '').strip()
        if username:
            user = app.models.user.User.query.filter(
                sqlalchemy.sql.func.lower(app.models.user.User.username) == username.lower()
            ).first()
            if not user:
                try:
                    user = create_external_user(username)
                except Exception as e:
                    app.utils.logger.log("ERROR", f"tide_connect create user failed: {e}")
                    return flask.make_response("", 401)
            return flask.make_response("", 200)

    # JWT cookie
    token = flask.request.cookies.get('access_token', '')
    if token:
        try:
            payload = pyjwt.decode(token, os.environ.get('SECRET_KEY', 'devsecret'), algorithms=["HS256"])
            if payload.get('userId'):
                return flask.make_response("", 200)
        except pyjwt.ExpiredSignatureError:
            app.utils.logger.log("WARNING", "tide_connect: JWT expired")
        except pyjwt.InvalidTokenError:
            pass

    return flask.make_response("", 401)

def _oidc_discover(issuer_url: str) -> dict:
    url = issuer_url.rstrip('/') + '/.well-known/openid-configuration'
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _oidc_redirect_uri(oidc_cfg: dict, slug: str) -> str:
    saved = (oidc_cfg.get('callbackURL') or '').strip()
    if saved:
        return saved
    domain = os.environ.get('DOMAIN', '').strip()
    if domain:
        return f"https://{domain}/api/auth/oidc/{slug}/callback"
    return flask.request.url_root.rstrip('/') + f"/api/auth/oidc/{slug}/callback"


@auth_bp.get('/api/auth/oidc/<string:slug>/login')
def oidc_login(slug):
    provider = app.models.auth_provider.AuthProvider.query.filter_by(slug=slug, type='oidc', enabled=True).first()
    if not provider:
        return flask.jsonify({"message": "Provider not found"}), 404

    oidc_cfg = (provider.settings or {}).get('oidc', {})
    issuer_url = oidc_cfg.get('issuerURL', '').rstrip('/')
    client_id = oidc_cfg.get('clientID', '')
    scopes = oidc_cfg.get('scopes', 'openid email profile')

    try:
        discovery = _oidc_discover(issuer_url)
    except Exception:
        return flask.jsonify({"message": "OIDC discovery failed"}), 502

    secret = os.environ.get('SECRET_KEY', 'devsecret')
    state = pyjwt.encode({
        "slug": slug,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
    }, secret, algorithm="HS256")

    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _oidc_redirect_uri(oidc_cfg, slug),
        "scope": scopes,
        "state": state,
    })
    return flask.redirect(discovery['authorization_endpoint'] + "?" + params)


@auth_bp.get('/api/auth/oidc/<string:slug>/callback')
def oidc_callback(slug):
    provider = app.models.auth_provider.AuthProvider.query.filter_by(slug=slug, type='oidc', enabled=True).first()
    if not provider:
        return flask.redirect('/?error=oidc_provider_not_found')

    secret = os.environ.get('SECRET_KEY', 'devsecret')
    state = flask.request.args.get('state', '')
    try:
        state_payload = pyjwt.decode(state, secret, algorithms=["HS256"])
        if state_payload.get('slug') != slug:
            raise ValueError("slug mismatch")
    except Exception:
        return flask.redirect('/?error=oidc_invalid_state')

    code = flask.request.args.get('code', '')
    if not code:
        return flask.redirect('/?error=oidc_no_code')

    oidc_cfg = (provider.settings or {}).get('oidc', {})
    issuer_url = oidc_cfg.get('issuerURL', '').rstrip('/')
    client_id = oidc_cfg.get('clientID', '')
    client_secret = oidc_cfg.get('clientSecret', '')
    username_claim = oidc_cfg.get('usernameClaim', 'preferred_username')

    try:
        discovery = _oidc_discover(issuer_url)
    except Exception:
        return flask.redirect('/?error=oidc_discovery_failed')

    token_resp = requests.post(discovery['token_endpoint'], data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _oidc_redirect_uri(oidc_cfg, slug),
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=10)

    if not token_resp.ok:
        return flask.redirect('/?error=oidc_token_exchange_failed')

    id_token = token_resp.json().get('id_token', '')
    try:
        claims = pyjwt.decode(id_token, options={"verify_signature": False})
    except Exception:
        return flask.redirect('/?error=oidc_invalid_id_token')

    username = claims.get(username_claim) or claims.get('email') or claims.get('sub', '')
    if not username:
        return flask.redirect('/?error=oidc_no_username')

    user = app.models.user.User.query.filter(
        sqlalchemy.sql.func.lower(app.models.user.User.username) == sqlalchemy.sql.func.lower(str(username))
    ).first()
    if not user:
        user = create_external_user(str(username))

    jwt_token = _generate_jwt(user, 'oidc', provider.name)
    resp = flask.redirect(f'/auth/login?token={urllib.parse.quote(jwt_token)}')
    resp.set_cookie('access_token', jwt_token, httponly=True, samesite='Lax', max_age=JWT_EXPIRY_HOURS * 3600, path='/')
    return resp


def generate_auth_token() -> str:
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(80))

def create_user(username, password, email, groups, usertype="Internal", protected=False):
    group_objects = app.models.user.Group.query.filter(app.models.user.Group.id.in_(groups)).all() if groups else []
    user = app.models.user.User(
        username=username.lower(),
        password=app.utils.extensions.bcrypt.generate_password_hash(password).decode('utf-8'),
        email=email.lower(),
        auth_token=generate_auth_token(),
        usertype=usertype,
        protected=protected,
    )
    user.groups = group_objects
    app.utils.extensions.db.session.add(user)
    app.utils.extensions.db.session.commit()
    return user
