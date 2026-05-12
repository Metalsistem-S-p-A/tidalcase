import json
import re
import flask
import app.utils.jwt_validator
import app.utils.permissions
import app.utils.extensions

auth_providers_bp = flask.Blueprint('auth_providers', __name__)


def _slugify(name: str) -> str:
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-')


def _require_admin():
    if not app.utils.permissions.Permissions.check_permission(flask.g.current_user.id, app.utils.permissions.Permissions.ADMIN_PANEL):
        return flask.jsonify({"success": False, "error": "Unauthorized"}), 403
    return None


@auth_providers_bp.get('/api/auth/providers')
@app.utils.jwt_validator.jwt_required
def list_providers():
    err = _require_admin()
    if err:
        return err

    page = int(flask.request.args.get('page', 0))
    limit = int(flask.request.args.get('limit', 0))
    sort_field = flask.request.args.get('sortField', 'priority')
    sort_order = int(flask.request.args.get('sortOrder', 1))

    q = app.models.auth_provider.AuthProvider.query

    # Sorting
    col = getattr(app.models.auth_provider.AuthProvider, sort_field, app.models.auth_provider.AuthProvider.priority)
    q = q.order_by(col.asc() if sort_order >= 0 else col.desc())

    total = q.count()

    if limit > 0:
        q = q.offset(page * limit).limit(limit)

    providers = q.all()
    return flask.jsonify({
        "data": [p.to_dict() for p in providers],
        "totalRecords": total,
    })


@auth_providers_bp.post('/api/auth/providers')
@app.utils.jwt_validator.jwt_required
def create_provider():
    err = _require_admin()
    if err:
        return err

    data = flask.request.get_json() or {}
    name = (data.get('name') or '').strip()
    ptype = (data.get('type') or '').strip()

    if not name or not ptype:
        return flask.jsonify({"success": False, "error": "name and type are required"}), 400

    slug = _slugify(name)
    # Ensure slug uniqueness
    base, counter = slug, 1
    while app.models.auth_provider.AuthProvider.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1

    provider = app.models.auth_provider.AuthProvider(
        name=name,
        slug=slug,
        type=ptype,
        priority=int(data.get('priority', 0)),
        enabled=bool(data.get('enabled', True)),
        settings=data.get('settings') or {},
    )
    app.utils.extensions.db.session.add(provider)
    app.utils.extensions.db.session.commit()
    return flask.jsonify(provider.to_dict()), 201


@auth_providers_bp.put('/api/auth/providers/<string:provider_id>')
@app.utils.jwt_validator.jwt_required
def update_provider(provider_id):
    err = _require_admin()
    if err:
        return err

    provider = app.utils.extensions.db.session.get(app.models.auth_provider.AuthProvider, provider_id)
    if not provider:
        return flask.jsonify({"success": False, "error": "Not found"}), 404

    # Prevent deleting the last local provider
    data = flask.request.get_json() or {}

    if 'name' in data:
        provider.name = data['name'].strip()
        # Re-generate slug only when name changes and it's not "local" (protected)
        if provider.type != 'local':
            new_slug = _slugify(provider.name)
            if new_slug != provider.slug:
                base, counter = new_slug, 1
                while app.models.auth_provider.AuthProvider.query.filter(
                    app.models.auth_provider.AuthProvider.slug == new_slug,
                    app.models.auth_provider.AuthProvider.id != provider.id
                ).first():
                    new_slug = f"{base}-{counter}"
                    counter += 1
                provider.slug = new_slug

    if 'priority' in data:
        provider.priority = int(data['priority'])
    if 'enabled' in data:
        provider.enabled = bool(data['enabled'])
    if 'settings' in data:
        provider.settings = data['settings'] or {}

    app.utils.extensions.db.session.commit()
    return flask.jsonify(provider.to_dict())


@auth_providers_bp.delete('/api/auth/providers/<string:provider_id>')
@app.utils.jwt_validator.jwt_required
def delete_provider(provider_id):
    err = _require_admin()
    if err:
        return err

    provider = app.utils.extensions.db.session.get(app.models.auth_provider.AuthProvider, provider_id)
    if not provider:
        return flask.jsonify({"success": False, "error": "Not found"}), 404

    if provider.type == 'local':
        return flask.jsonify({"success": False, "error": "Cannot delete the local auth provider"}), 400

    app.utils.extensions.db.session.delete(provider)
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})
