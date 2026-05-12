import uuid
import sqlalchemy
import app.utils.extensions

class Registry(app.utils.extensions.db.Model):
    id = app.utils.extensions.db.Column(app.utils.extensions.db.UUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    url = app.utils.extensions.db.Column(app.utils.extensions.db.String(255), nullable=False)
