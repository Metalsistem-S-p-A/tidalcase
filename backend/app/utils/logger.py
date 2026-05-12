import os
import app.models.log
import app.utils.extensions

def log(level: str, message: str):
    try:
        log_entry = app.models.log.Log(level=level, message=message)
        app.utils.extensions.db.session.add(log_entry)
        app.utils.extensions.db.session.commit()

        timestamp = log_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')

        # Only print DEBUG logs if in debug mode
        debug_mode = os.environ.get('FLASK_DEBUG') == '1'

        if level != "DEBUG" or debug_mode:
            print(f"[{level}] | {timestamp} | {message}", flush=True)

        return log_entry
    except Exception:
        pass
    return None
