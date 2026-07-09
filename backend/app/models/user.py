import typing
import uuid
import sqlalchemy
import app.utils.extensions

user_groups = app.utils.extensions.db.Table(
    'user_groups',
    app.utils.extensions.db.Column('user_id', app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('user.id'), nullable=False),
    app.utils.extensions.db.Column('group_id', app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('group.id'), nullable=False),
)

class User(app.utils.extensions.db.Model):
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), unique=True, nullable=False)
    password = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    auth_token = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    email = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    preferred_language = app.utils.extensions.db.Column(app.utils.extensions.db.String(8), nullable=False, default='en')
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    usertype = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=False, default="Internal")
    protected = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=False)
    mfa_secret = app.utils.extensions.db.Column(app.utils.extensions.db.String(64), nullable=True)
    mfa_enabled = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=False)
    mfa_trust_duration = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=False, default=30)
    auto_start_tide_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), nullable=True)

    groups = app.utils.extensions.db.relationship('Group', secondary=user_groups, lazy='select')

    def get_groups(self) -> list[str]:
        return [str(g.id) for g in self.groups]

    def has_permission(self, permission):
        return app.utils.permissions.Permissions.check_permission(self.id, permission)

    def setting_value(self, setting) -> typing.Optional[typing.Any]:
        groups = sorted(self.groups, key=lambda g: g.priority, reverse=True)
        for group in groups:
            val = (group.settings or {}).get(setting)
            if val is not None:
                return val
        return None

    def get_settings(self) -> dict:
        result = {}
        groups = sorted(self.groups, key=lambda g: g.priority)
        for group in groups:
            result.update({k: v for k, v in (group.settings or {}).items() if v is not None})
        if self.auto_start_tide_id:
            result['auto_start_tide_id'] = str(self.auto_start_tide_id)
        if self.preferred_language:
            result['preferred_language'] = self.preferred_language
        return result


class Group(app.utils.extensions.db.Model):
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    protected = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_admin_panel = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_view_instances = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_edit_instances = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_view_users = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_edit_users = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_view_tides = app.utils.extensions.db.Column('perm_view_tides', app.utils.extensions.db.Boolean, nullable=False)
    perm_edit_tides = app.utils.extensions.db.Column('perm_edit_tides', app.utils.extensions.db.Boolean, nullable=False)
    perm_view_registry = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_edit_registry = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_view_groups = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    perm_edit_groups = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False)
    priority = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=False, default=0)
    settings = app.utils.extensions.db.Column(app.utils.extensions.db.JSON, nullable=True)
    auto_start_tide_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), nullable=True)


class RefreshToken(app.utils.extensions.db.Model):
    __tablename__ = 'refresh_token'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('user.id'), nullable=False)
    token = app.utils.extensions.db.Column(app.utils.extensions.db.String(64), nullable=False, unique=True)
    expires_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, nullable=False)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text('CURRENT_TIMESTAMP'))
    auth_provider_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('auth_provider.id'), nullable=True)


class TrustedDevice(app.utils.extensions.db.Model):
    __tablename__ = 'trusted_device'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('user.id'), nullable=False)
    device_name = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    ip_address = app.utils.extensions.db.Column(app.utils.extensions.db.String(45), nullable=True)
    last_used_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text('CURRENT_TIMESTAMP'))
    expires_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, nullable=False)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text('CURRENT_TIMESTAMP'))
