import uuid
import datetime
import sqlalchemy
import app.utils.extensions

tide_agents = app.utils.extensions.db.Table(
    'tide_agents',
    app.utils.extensions.db.Column('tide_id', app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('tide.id'), nullable=False),
    app.utils.extensions.db.Column('agent_id', app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('agent.id'), nullable=False),
)

class Tide(app.utils.extensions.db.Model):
    __tablename__ = 'tide'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=False)
    description = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    image_path = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    tide_type = app.utils.extensions.db.Column('tide_type', app.utils.extensions.db.String(80), nullable=False)
    container_docker_image = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    container_docker_registry = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    container_cores = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=True)
    container_memory = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=True)
    container_swap = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=True)
    container_shm = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=True)
    container_network = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    server_ip = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    server_port = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=True)
    restricted_groups = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=True)
    session_time_limit = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=True, default=0)
    session_idle_time_limit = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, nullable=True, default=0)
    agent_selection_mode = app.utils.extensions.db.Column(app.utils.extensions.db.String(20), nullable=True)
    vnc_user = app.utils.extensions.db.Column(app.utils.extensions.db.String(80), nullable=True)
    upload_path = app.utils.extensions.db.Column(app.utils.extensions.db.String(), nullable=True)
    download_path = app.utils.extensions.db.Column(app.utils.extensions.db.String(), nullable=True)
    open_mode = app.utils.extensions.db.Column(app.utils.extensions.db.String(10), nullable=False, default='user', server_default='user')
    connection_settings = app.utils.extensions.db.Column(app.utils.extensions.db.JSON, nullable=True)

    agents = app.utils.extensions.db.relationship('Agent', secondary=tide_agents, lazy='select')
    env_vars = app.utils.extensions.db.relationship('TideEnv', backref='tide', cascade='all, delete-orphan', lazy='select')

    def get_agents(self) -> list[str]:
        return [str(g.id) for g in self.agents]

class TideInstance(app.utils.extensions.db.Model):
    __tablename__ = 'tide_instance'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tide_id = app.utils.extensions.db.Column('tide_id', app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('tide.id'), nullable=False)
    user_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('user.id'), nullable=False)
    agent_id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), app.utils.extensions.db.ForeignKey('agent.id'), nullable=True)
    vnc_password = app.utils.extensions.db.Column(app.utils.extensions.db.String(32), nullable=True)
    direct_url = app.utils.extensions.db.Column(app.utils.extensions.db.String(512), nullable=True)
    guac_token = app.utils.extensions.db.Column(app.utils.extensions.db.Text, nullable=True)
    paused = app.utils.extensions.db.Column(app.utils.extensions.db.Boolean, nullable=False, default=False, server_default='false')
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    updated_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"), onupdate=datetime.datetime.now())


class TideEnv(app.utils.extensions.db.Model):
    """Container environment variables tied to a Tide.

    Each row is one env var passed to the container at launch. Values set here
    are MERGED with the runtime-computed ones (VNC_PW, DISPLAY, locale, TZ),
    but the runtime ones win on key collision to avoid breaking the session.
    """
    __tablename__ = 'tide_env'
    id = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, primary_key=True, autoincrement=True)
    tide_id = app.utils.extensions.db.Column(
        app.utils.extensions.db.UUID(),
        app.utils.extensions.db.ForeignKey('tide.id', ondelete='CASCADE'),
        nullable=False,
    )
    key = app.utils.extensions.db.Column(app.utils.extensions.db.String(128), nullable=False)
    value = app.utils.extensions.db.Column(app.utils.extensions.db.Text, nullable=False, default='', server_default='')

    __table_args__ = (
        app.utils.extensions.db.UniqueConstraint('tide_id', 'key', name='uq_tide_env_tide_key'),
    )
