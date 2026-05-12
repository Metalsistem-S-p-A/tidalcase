import json
import uuid
import sqlalchemy
import app.utils.extensions


class StorageProvider(app.utils.extensions.db.Model):
    __tablename__ = 'storage_provider'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    enabled = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=True)
    provider_type = app.utils.extensions.db.Column(app.utils.extensions.db.String(40), nullable=False, default='rclone')
    default_destination = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=False, default='/storage')
    volume_config = app.utils.extensions.db.Column(app.utils.extensions.db.Text, nullable=True)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))

    def get_volume_config(self) -> dict:
        try:
            return json.loads(self.volume_config) if self.volume_config else {}
        except Exception:
            return {}


class TideStorageMount(app.utils.extensions.db.Model):
    __tablename__ = 'tide_storage_mount'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tide_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('tide.id'), nullable=False)
    storage_provider_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('storage_provider.id'), nullable=False)
    enabled = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=True)
    read_only = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=False)
    destination = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
