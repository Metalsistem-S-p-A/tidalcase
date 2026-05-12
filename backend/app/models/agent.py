import uuid
import sqlalchemy
import app.utils.extensions

class Agent(app.utils.extensions.db.Model):
    __tablename__ = 'agent'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    docker_host = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=False)
    total_cores = app.utils.extensions.db.Column(app.utils.extensions.db.Float, nullable=True)
    total_memory = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=True)
    enabled = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, default=True, nullable=False)
    prune_mode = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=False, default='off')
    api_url = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    api_token = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    healthy = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=True)
    last_healthcheck_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, nullable=True)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
