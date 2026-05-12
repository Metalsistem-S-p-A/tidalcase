#!/usr/bin/env python3
import http.server
import json
import mimetypes
import os
import urllib.parse
import requests

REGISTRY_INTERNAL = os.environ.get('REGISTRY_INTERNAL_URL', 'http://127.0.0.1:5001')
CATALOG_PORT = int(os.environ.get('CATALOG_PORT', '5000'))
REGISTRY_NAME = os.environ.get('REGISTRY_NAME', 'Tidalcase Registry')
IMAGE_PREFIX = os.environ.get('REGISTRY_IMAGE_PREFIX', '').rstrip('/')
ICONS_DIR = os.environ.get('ICONS_DIR', '/icons')

HOP_BY_HOP = frozenset([
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
])

MANIFEST_ACCEPT_ALL = ', '.join([
    'application/vnd.docker.distribution.manifest.v2+json',
    'application/vnd.docker.distribution.manifest.list.v2+json',
    'application/vnd.oci.image.manifest.v1+json',
    'application/vnd.oci.image.index.v1+json',
])

MANIFEST_ACCEPT_SINGLE = ', '.join([
    'application/vnd.docker.distribution.manifest.v2+json',
    'application/vnd.oci.image.manifest.v1+json',
])


def _resolve_manifest(repo, ref):
    resp = requests.get(
        f"{REGISTRY_INTERNAL}/v2/{repo}/manifests/{ref}",
        headers={'Accept': MANIFEST_ACCEPT_ALL},
        timeout=5,
    )
    resp.raise_for_status()
    manifest = resp.json()
    media_type = manifest.get('mediaType') or resp.headers.get('Content-Type', '')

    if any(t in media_type for t in ('index', 'list')):
        manifests = manifest.get('manifests', [])
        target = next(
            (m for m in manifests
             if m.get('platform', {}).get('architecture') == 'amd64'
             and m.get('platform', {}).get('os') == 'linux'),
            manifests[0] if manifests else None,
        )
        if not target:
            return None
        resp = requests.get(
            f"{REGISTRY_INTERNAL}/v2/{repo}/manifests/{target['digest']}",
            headers={'Accept': MANIFEST_ACCEPT_SINGLE},
            timeout=5,
        )
        resp.raise_for_status()
        manifest = resp.json()

    return manifest


def get_image_labels(repo, tag):
    try:
        manifest = _resolve_manifest(repo, tag)
        if not manifest:
            return {}
        config_digest = manifest.get('config', {}).get('digest')
        if not config_digest:
            return {}
        blob_resp = requests.get(
            f"{REGISTRY_INTERNAL}/v2/{repo}/blobs/{config_digest}",
            timeout=5,
        )
        blob_resp.raise_for_status()
        return blob_resp.json().get('config', {}).get('Labels') or {}
    except Exception as e:
        print(f"[labels] {repo}:{tag} error: {e}", flush=True)
        return {}


def build_list_json():
    try:
        catalog = requests.get(f"{REGISTRY_INTERNAL}/v2/_catalog", timeout=5)
        catalog.raise_for_status()
        repositories = catalog.json().get('repositories') or []
    except Exception:
        return {'name': REGISTRY_NAME, 'workspaces': []}

    workspaces = []
    for repo in repositories:
        try:
            tags_resp = requests.get(f"{REGISTRY_INTERNAL}/v2/{repo}/tags/list", timeout=5)
            tags_resp.raise_for_status()
            tags = sorted(tags_resp.json().get('tags') or [])
        except Exception:
            tags = []

        ref_tag = 'latest' if 'latest' in tags else (tags[-1] if tags else None)
        labels = get_image_labels(repo, ref_tag) if ref_tag else {}

        raw_cats = labels.get('tidalcase.categories', '')
        categories = [c.strip() for c in raw_cats.split(',') if c.strip()]

        workspaces.append({
            'friendly_name': labels.get('org.opencontainers.image.title') or repo.split('/')[-1],
            'description': labels.get('org.opencontainers.image.description') or '',
            'categories': categories,
            'image_src': labels.get('tidalcase.icon', ''),
            'architecture': [a.strip() for a in labels.get('tidalcase.architecture', '').split(',') if a.strip()],
            'compatibility': [
                {'version': tag, 'image': f"{IMAGE_PREFIX}/{repo}:{tag}"}
                for tag in tags
            ],
            'docker_registry': IMAGE_PREFIX,
        })

    return {'name': REGISTRY_NAME, 'workspaces': workspaces}


class Handler(http.server.BaseHTTPRequestHandler):
    def handle_request(self):
        path = urllib.parse.urlparse(self.path).path

        if self.command == 'GET' and path in ('/', '/list.json'):
            body = json.dumps(build_list_json()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.command == 'GET' and path.startswith('/icons/'):
            filename = os.path.basename(path[7:])
            filepath = os.path.join(ICONS_DIR, filename)
            if filename and os.path.isfile(filepath):
                with open(filepath, 'rb') as f:
                    data = f.read()
                ctype = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        req_body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP | {'host'}}

        try:
            resp = requests.request(
                self.command,
                f"{REGISTRY_INTERNAL}{self.path}",
                headers=headers,
                data=req_body,
                stream=True,
                timeout=60,
            )
            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.end_headers()
            for chunk in resp.iter_content(chunk_size=65536):
                self.wfile.write(chunk)
        except Exception:
            self.send_response(502)
            self.end_headers()

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = handle_request

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    print(f"Catalog server :{CATALOG_PORT} → {REGISTRY_INTERNAL}", flush=True)
    http.server.HTTPServer(('0.0.0.0', CATALOG_PORT), Handler).serve_forever()
