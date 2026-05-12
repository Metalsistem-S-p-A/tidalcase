import sqlalchemy
import app.utils.extensions

class Log(app.utils.extensions.db.Model):
    id = app.utils.extensions.db.Column(app.utils.extensions.db.Integer, primary_key=True)
    created_at = app.utils.extensions.db.Column(app.utils.extensions.db.DateTime, server_default=sqlalchemy.text("CURRENT_TIMESTAMP"))
    level = app.utils.extensions.db.Column(app.utils.extensions.db.String(8), nullable=False) #DEBUG, INFO, WARNING, ERROR
    message = app.utils.extensions.db.Column(app.utils.extensions.db.String(1024), nullable=False)
