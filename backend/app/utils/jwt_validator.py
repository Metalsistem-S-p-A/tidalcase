import os
import functools
import flask
import jwt as pyjwt
import app.models.user
import app.utils.logger


def jwt_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if getattr(flask.g, 'current_user', None) is not None:
            return f(*args, **kwargs)
        token = flask.request.cookies.get('access_token', '')
        if not token:
            app.utils.logger.log("WARNING", f"jwt_required [{f.__name__}]: no access_token cookie (cookies: {list(flask.request.cookies.keys())})")
            return flask.jsonify({"message": "auth.loginFailed"}), 401
        try:
            secret = os.environ.get('SECRET_KEY', 'devsecret')
            payload = pyjwt.decode(token, secret, algorithms=["HS256"])
            user_id = payload.get('userId')
            if not user_id:
                app.utils.logger.log("WARNING", f"jwt_required [{f.__name__}]: no userId in token payload")
                return flask.jsonify({"message": "auth.loginFailed"}), 401
            user = app.models.user.User.query.filter_by(id=user_id).first()
            if not user:
                app.utils.logger.log("WARNING", f"jwt_required [{f.__name__}]: user not found for id={user_id}")
                return flask.jsonify({"message": "auth.loginFailed"}), 401
            flask.g.current_user = user
            return f(*args, **kwargs)
        except pyjwt.ExpiredSignatureError:
            app.utils.logger.log("WARNING", f"jwt_required [{f.__name__}]: token expired")
            return flask.jsonify({"message": "auth.sessionExpired"}), 401
        except pyjwt.InvalidTokenError as e:
            app.utils.logger.log("WARNING", f"jwt_required [{f.__name__}]: invalid token: {e}")
            return flask.jsonify({"message": "auth.loginFailed"}), 401
    return wrapper
