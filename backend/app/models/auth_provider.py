import uuid
import sqlalchemy
import app.utils.extensions

class AuthProvider(app.utils.extensions.db.Model):
    __tablename__ = 'auth_provider'

    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    slug = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False, unique=True)
    type = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=False)   # local | ldap | azure-ad | oidc
    priority = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=False, default=0)
    enabled = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=True)
    settings = app.utils.extensions.db.Column(app.utils.extensions.db.JSON, nullable=True)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))

    def to_dict(self):
        return {
            '_id': self.id,
            'name': self.name,
            'slug': self.slug,
            'type': self.type,
            'priority': self.priority,
            'enabled': self.enabled,
            'settings': self.settings or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
