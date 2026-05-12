import io
import os
import tarfile
import flask
import docker.errors

files_bp = flask.Blueprint('files', __name__)

_AGENT_NET      = 'tidalcase-network'


def _get_container(name: str):
    try:
        return docker.from_env().containers.get(name)
    except docker.errors.NotFound:
        return None

@files_bp.get('/container/<string:name>/downloads')
def list_downloads(name: str):
    container = _get_container(name)
    if container is None:
        return flask.jsonify({'ok': False, 'error': 'container not found'}), 404

    download_path = flask.request.args.get('download_path', '')
    if not download_path:
        return flask.jsonify({'ok': False, 'error': 'download_path is required'}), 400

    result = container.exec_run(
        ['find', download_path, '-maxdepth', '1', '-type', 'f',
         '-printf', '%f|%s|%Ts\n'],
        user='root',
    )

    files = []
    if result.exit_code == 0:
        for line in result.output.decode('utf-8', errors='replace').splitlines():
            parts = line.split('|', 2)
            if len(parts) == 3:
                fname, size_s, ts_s = parts
                try:
                    files.append({
                        'name': fname,
                        'size': int(size_s),
                        'modified': float(ts_s),
                    })
                except ValueError:
                    pass

    files.sort(key=lambda f: f['modified'], reverse=True)
    return flask.jsonify({'ok': True, 'files': files})


@files_bp.get('/container/<string:name>/downloads/<string:filename>')
def download_file(name: str, filename: str):
    if '..' in filename or filename.startswith('/') or os.sep in filename:
        return flask.jsonify({'ok': False, 'error': 'invalid filename'}), 400

    container = _get_container(name)
    if container is None:
        return flask.jsonify({'ok': False, 'error': 'container not found'}), 404

    download_path = flask.request.args.get('download_path', '')
    if not download_path:
        return flask.jsonify({'ok': False, 'error': 'download_path is required'}), 400

    try:
        bits, _ = container.get_archive(f'{download_path}/{filename}')
    except Exception:
        return flask.jsonify({'ok': False, 'error': 'file not found'}), 404

    def _generate():
        buf = io.BytesIO()
        for chunk in bits:
            buf.write(chunk)
        buf.seek(0)
        with tarfile.open(fileobj=buf) as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            if members:
                f = tar.extractfile(members[0])
                if f:
                    while True:
                        data = f.read(65536)
                        if not data:
                            break
                        yield data

    return flask.Response(
        flask.stream_with_context(_generate()),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/octet-stream',
        }
    )


@files_bp.post('/container/<string:name>/uploads')
def upload_file(name: str):
    incoming = flask.request.files.getlist('file[]')
    if not incoming:
        return flask.jsonify({'ok': False, 'error': 'no files provided'}), 400

    container = _get_container(name)
    if container is None:
        return flask.jsonify({'ok': False, 'error': 'container not found'}), 404

    path = flask.request.args.get('upload_path', '')
    if not path:
        return flask.jsonify({'ok': False, 'error': 'upload_path is required'}), 400

    container.exec_run(['mkdir', '-p', path], user='root')

    buf = io.BytesIO()
    uploaded = []
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for file in incoming:
            safe_name = os.path.basename(file.filename or '')
            if not safe_name or '..' in safe_name:
                continue
            file_data = file.read()
            info = tarfile.TarInfo(name=safe_name)
            info.size  = len(file_data)
            info.mode  = 0o644
            info.uid   = 1000
            info.gid   = 1000
            info.uname = 'kasm-user'
            info.gname = 'kasm-user'
            tar.addfile(info, io.BytesIO(file_data))
            uploaded.append(safe_name)
    buf.seek(0)

    if not uploaded:
        return flask.jsonify({'ok': False, 'error': 'no valid files'}), 400

    try:
        container.put_archive(path, buf.read())
    except Exception as e:
        return flask.jsonify({'ok': False, 'error': str(e)}), 500

    return flask.jsonify({'ok': True, 'names': uploaded})
