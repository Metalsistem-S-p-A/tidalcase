import sys
import os
import flask
import celery
import routes.health
import routes.container
import routes.network
import routes.prune
import routes.volume
import routes.config
import routes.files
import utils

# TIDALCASE_JOIN_TOKEN — the manager's shared join token (one per manager).
# All agents use this to prove they are authorized to register.
if not utils.JOIN_TOKEN:
    raise RuntimeError("TIDALCASE_JOIN_TOKEN is required")

is_celery = 'celery' in os.environ.get('_', '').lower() or any('celery' in arg for arg in sys.argv)

if os.environ.get("TIDALCASE_CERTS_HOST_DIR") and not is_celery:
    for _f in ("/certs/tidalcase.crt", "/certs/tidalcase.key"):
        if not os.path.exists(_f):
            raise RuntimeError(
                f"TIDALCASE_CERTS_HOST_DIR is set but {_f} is missing. "
                "Place tidalcase.crt and tidalcase.key in the certs directory."
            )

def create_app():
    flask_app = flask.Flask(__name__)

    @flask_app.before_request
    def check_auth():
        auth = flask.request.headers.get("Authorization", "")
        if auth != f"Bearer {utils.MY_API_TOKEN}":
            return flask.jsonify({"ok": False, "error": "Unauthorized"}), 401
        return None

    flask_app.register_blueprint(routes.health.bp)
    flask_app.register_blueprint(routes.container.bp)
    flask_app.register_blueprint(routes.volume.bp)
    flask_app.register_blueprint(routes.network.bp)
    flask_app.register_blueprint(routes.prune.bp)
    flask_app.register_blueprint(routes.config.bp)
    flask_app.register_blueprint(routes.files.files_bp)

    return flask_app

def make_celery(app):
    class FlaskTask(celery.Task):
        def run(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_instance = celery.Celery(app.import_name)
    celery_instance.conf.update(
        broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://tidalcase-redis:6379/1'),
        result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://tidalcase-redis:6379/1'),
        task_ignore_result=True,
        imports=[
            'celery_tasks.register',
            'celery_tasks.heartbeat',
            'celery_tasks.container',
            'celery_tasks.prune',
        ]
    )

    celery_instance.conf.beat_schedule = {
        'send-heartbeat-every-30-seconds': {
            'task': 'celery_tasks.heartbeat.send_heartbeat',
            'schedule': 30.0,
            'options': {'queue': 'monitor'},
        },
        'prune-images-every-hour': {
            'task': 'celery_tasks.prune.prune_images',
            'schedule': 3600.0,
            'options': {'queue': 'monitor'},
        },
        'check-containers-every-10-seconds': {
            'task': 'celery_tasks.container.check_containers',
            'schedule': 10.0,
            'options': {'queue': 'monitor'},
        },
    }

    celery_instance.conf.task_routes = {
        'celery_tasks.container.monitor_container': {'queue': 'monitor'},
        'celery_tasks.container.check_containers': {'queue': 'monitor'},
        'celery_tasks.container.pull_image': {'queue': 'monitor'},
        'celery_tasks.heartbeat.send_heartbeat': {'queue': 'monitor'},
        'celery_tasks.prune.prune_images': {'queue': 'monitor'},
        'celery_tasks.register.register_agent': {'queue': 'monitor'},
    }

    celery_instance.Task = FlaskTask
    return celery_instance

agent_app = create_app()
celery_app = make_celery(agent_app)
