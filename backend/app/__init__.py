import os
import flask
import app.utils.extensions
import app.routes.auth
import app.routes.admin
import app.routes.tide
import app.routes.agent_api
import app.routes.auth_providers
import app.routes.users

__version__ = "1.0.1"

def create_app():
    flask_app = flask.Flask(__name__)

    flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///data/tidalcase.db'
    )
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.utils.extensions.db.init_app(flask_app)
    app.utils.extensions.bcrypt.init_app(flask_app)

    flask_app.register_blueprint(app.routes.auth.auth_bp)
    flask_app.register_blueprint(app.routes.admin.admin_bp, url_prefix='/api/admin')
    flask_app.register_blueprint(app.routes.tide.tide_bp)
    flask_app.register_blueprint(app.routes.agent_api.agent_api_bp)
    flask_app.register_blueprint(app.routes.auth_providers.auth_providers_bp)
    flask_app.register_blueprint(app.routes.users.users_bp)

    return flask_app
