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
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    updated_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"), onupdate=datetime.datetime.now())
