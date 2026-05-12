import os
import string
import random
import run
import flask_migrate
import app.models.user
import app.routes.auth
import app.utils.extensions
import app.utils.logger

def create_default_users():
    """Create default admin and user accounts if none exist."""
    if app.models.user.User.query.count() > 0:
        return

    admin_group = app.models.user.Group.query.filter_by(id="00000000-0000-0000-0000-000000000000").first()
    user_group = app.models.user.Group.query.filter_by(id="00000000-0000-0000-0000-000000000001").first()

    admin_pw = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    app.routes.auth.create_user("admin", admin_pw, '', [admin_group.id, user_group.id], protected=True)

    user_pw = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    app.routes.auth.create_user("user", user_pw, '', [user_group.id])

    print()
    print("Created default users:")
    print("-----------------------")
    print("Username: admin")
    print(f"Password: {admin_pw}")
    print("-----------------------")
    print("Username: user")
    print(f"Password: {user_pw}")
    print("-----------------------")
    print()

def _ensure_join_token():
    """Generate and persist the manager's agent join token on first run."""
    token_path = "data/join_token"
    if not os.path.exists(token_path):
        chars = string.ascii_letters + string.digits + '-_'
        token = ''.join(random.choice(chars) for _ in range(43))
        with open(token_path, 'w', encoding="utf-8") as f:
            f.write(token)
        app.utils.logger.log("INFO", "Generated agent join token (data/join_token)")
    with open(token_path, 'r', encoding="utf-8") as f:
        return f.read().strip()

def initialize_app():
    app.utils.logger.log("INFO", "Initializing Tidalcase...")
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/tide_images", exist_ok=True)
    _ensure_join_token()
    create_default_users()
    app.utils.logger.log("INFO", "Tidalcase initialized.")

def setup():
    with run.tidalcase_app.app_context():
        migrate = flask_migrate.Migrate()
        migrate.init_app(run.tidalcase_app, app.utils.extensions.db, render_as_batch=True)
        flask_migrate.upgrade()
        initialize_app()

if __name__ == "__main__":
    setup()
