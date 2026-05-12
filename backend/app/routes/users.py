import io
import base64
import datetime
import flask
import app.utils.jwt_validator
import pyotp
import qrcode
import app.models.user
import app.utils.extensions
import app.utils.logger

users_bp = flask.Blueprint('users', __name__)


def _qr_data_url(uri: str) -> str:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@users_bp.get('/api/users/me')
@app.utils.jwt_validator.jwt_required
def get_me():
    user = flask.g.current_user
    return flask.jsonify({
        "id": str(user.id),
        "username": user.username,
        "email": user.email or '',
        "mfaEnabled": bool(user.mfa_enabled),
        "mfaTrustDuration": user.mfa_trust_duration or 30,
        "usertype": user.usertype,
        "autostartTideId": user.auto_start_tide_id
    })


@users_bp.put('/api/users/email')
@app.utils.jwt_validator.jwt_required
def update_email():
    data = flask.request.get_json() or {}
    email = (data.get('email') or '').strip()

    user = flask.g.current_user
    user.email = email or None
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})

@users_bp.put('/api/users/autostart-tide')
@app.utils.jwt_validator.jwt_required
def update_autostart():
    data = flask.request.get_json() or {}
    tide_id = data.get('tide_id') or None

    user = flask.g.current_user
    user.auto_start_tide_id = tide_id
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.post('/api/users/change-password')
@app.utils.jwt_validator.jwt_required
def change_password():
    data = flask.request.get_json() or {}
    current_password = data.get('currentPassword', '')
    new_password = data.get('newPassword', '')

    user = flask.g.current_user
    if not app.utils.extensions.bcrypt.check_password_hash(user.password, current_password):
        return flask.jsonify({"message": "auth.errors.incorrectPassword"}), 400

    if len(new_password) < 6:
        return flask.jsonify({"message": "auth.errors.passwordTooShort"}), 400

    user.password = app.utils.extensions.bcrypt.generate_password_hash(new_password).decode('utf-8')
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.post('/api/users/mfa/setup')
@app.utils.jwt_validator.jwt_required
def mfa_setup():
    user = flask.g.current_user
    if user.mfa_enabled:
        return flask.jsonify({"message": "MFA already enabled"}), 400

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.username, issuer_name="Tidalcase")

    user.mfa_secret = secret
    app.utils.extensions.db.session.commit()

    return flask.jsonify({
        "secret": secret,
        "qrCode": _qr_data_url(uri),
    })


@users_bp.post('/api/users/mfa/verify')
@app.utils.jwt_validator.jwt_required
def mfa_verify():
    data = flask.request.get_json() or {}
    token = (data.get('token') or '').strip()

    user = flask.g.current_user
    if not user.mfa_secret:
        return flask.jsonify({"message": "MFA setup not started"}), 400

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(token, valid_window=2):
        return flask.jsonify({"message": "mfa.errors.invalid"}), 400

    user.mfa_enabled = True
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.post('/api/users/mfa/disable')
@app.utils.jwt_validator.jwt_required
def mfa_disable():
    data = flask.request.get_json() or {}
    password = data.get('password', '')
    token = (data.get('token') or '').strip()

    user = flask.g.current_user

    if user.usertype == 'Internal':
        if not app.utils.extensions.bcrypt.check_password_hash(user.password, password):
            return flask.jsonify({"message": "auth.errors.incorrectPassword"}), 400

    if not user.mfa_secret:
        return flask.jsonify({"message": "MFA not configured"}), 400

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(token, valid_window=2):
        return flask.jsonify({"message": "mfa.errors.invalid"}), 400

    user.mfa_enabled = False
    user.mfa_secret = None
    app.models.user.TrustedDevice.query.filter_by(user_id=str(user.id)).delete()
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.put('/api/users/mfa/trust-duration')
@app.utils.jwt_validator.jwt_required
def update_trust_duration():
    data = flask.request.get_json() or {}
    duration = data.get('mfaTrustDuration', 30)
    if not isinstance(duration, int) or duration < 0 or duration > 365:
        return flask.jsonify({"message": "Invalid duration"}), 400

    user = flask.g.current_user
    user.mfa_trust_duration = duration
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.get('/api/users/mfa/trusted-devices')
@app.utils.jwt_validator.jwt_required
def get_trusted_devices():
    user_id = str(flask.g.current_user.id)
    now = datetime.datetime.now(datetime.timezone.utc)
    devices = app.models.user.TrustedDevice.query.filter(
        app.models.user.TrustedDevice.user_id == user_id,
        app.models.user.TrustedDevice.expires_at > now,
    ).order_by(app.models.user.TrustedDevice.last_used_at.desc()).all()

    return flask.jsonify([{
        "deviceId": str(d.id),
        "deviceName": d.device_name,
        "ipAddress": d.ip_address,
        "lastUsedAt": d.last_used_at.isoformat() if d.last_used_at else None,
        "expiresAt": d.expires_at.isoformat() if d.expires_at else None,
    } for d in devices])


@users_bp.delete('/api/users/mfa/trusted-devices/<string:device_id>')
@app.utils.jwt_validator.jwt_required
def revoke_trusted_device(device_id: str):
    user_id = str(flask.g.current_user.id)
    device = app.models.user.TrustedDevice.query.filter_by(id=device_id, user_id=user_id).first()
    if not device:
        return flask.jsonify({"message": "Not found"}), 404
    app.utils.extensions.db.session.delete(device)
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})


@users_bp.delete('/api/users/mfa/trusted-devices')
@app.utils.jwt_validator.jwt_required
def revoke_all_trusted_devices():
    user_id = str(flask.g.current_user.id)
    app.models.user.TrustedDevice.query.filter_by(user_id=user_id).delete()
    app.utils.extensions.db.session.commit()
    return flask.jsonify({"success": True})
