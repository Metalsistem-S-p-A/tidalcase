"""HTTP client for tidalcase-agent services."""
import typing
import requests


class AgentError(Exception):
    pass


class AgentPullingError(AgentError):
    pass

class AgentHTTPClient:
    def __init__(self, api_url: str, api_token: str):
        self.base = api_url.rstrip('/')
        self._headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
        }

    def _get(self, path: str, params: dict = None, timeout: int = 10) -> dict:
        try:
            r = requests.get(f'{self.base}{path}', headers=self._headers,
                             params=params, timeout=timeout)
            data = r.json()
        except Exception as e:
            raise AgentError(str(e)) from e
        if not data.get('ok'):
            raise AgentError(data.get('error', 'unknown error'))
        return data

    def _post(self, path: str, body: dict = None, timeout: int = 10) -> dict:
        try:
            r = requests.post(f'{self.base}{path}', headers=self._headers,
                              json=body or {}, timeout=timeout)
            data = r.json()
        except Exception as e:
            raise AgentError(str(e)) from e
        if not data.get('ok'):
            if data.get('pulling'):
                raise AgentPullingError(data.get('error', 'image pull in progress'))
            raise AgentError(data.get('error', 'unknown error'))
        return data

    def _delete(self, path: str, timeout: int = 10) -> dict:
        try:
            r = requests.delete(f'{self.base}{path}', headers=self._headers,
                                timeout=timeout)
            data = r.json()
        except Exception as e:
            raise AgentError(str(e)) from e
        return data

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def ping(self) -> bool:
        try:
            self._get('/health', timeout=5)
            return True
        except Exception as e:
            print(e)
            return False

    def get_info(self) -> dict:
        return self._get('/health')

    # ------------------------------------------------------------------
    # Containers
    # ------------------------------------------------------------------
    def run_container(self, image: str, name: str, env: dict,
                      mem_limit, cpu_shares: int,
                      network: str = None, ports: dict = None,
                      mounts: list = None, config_files: list = None,
                      shm_size: int = None, extra_hosts: dict = None,
                      auth_header: str = None,
                      session_time_limit_s: int = None,
                      memswap_limit: str = None) -> dict:
        return self._post('/container/run', {
            'image': image,
            'name': name,
            'env': env or {},
            'mem_limit': mem_limit,
            'memswap_limit': memswap_limit,
            'cpu_shares': cpu_shares,
            'network': network,
            'ports': ports,
            'mounts': mounts or [],
            'config_files': config_files or [],
            'shm_size': shm_size,
            'extra_hosts': extra_hosts or {},
            'auth_header': auth_header or '',
            'session_time_limit_s': session_time_limit_s,
        }, timeout=60)

    def remove_container(self, name: str) -> None:
        self._delete(f'/container/{name}')

    def pause_container(self, name: str) -> None:
        self._post(f'/container/{name}/pause')

    def unpause_container(self, name: str) -> None:
        self._post(f'/container/{name}/unpause')

    def get_container_ip(self, name: str, network: str) -> typing.Optional[str]:
        data = self._get(f'/container/{name}/ip', params={'network': network})
        return data.get('ip')
    
    def instance_check(self, name: str) -> typing.Optional[bool]:
        data = self._get(f'/container/{name}')
        return data.get('ok')

    # ------------------------------------------------------------------
    # Volumes / Networks
    # ------------------------------------------------------------------
    def ensure_volume(self, name: str, driver: str = 'local', driver_opts: dict = None) -> None:
        self._post('/volume/ensure', {'name': name, 'driver': driver, 'driver_opts': driver_opts or {}})

    def ensure_network(self, name: str) -> None:
        self._post('/network/ensure', {'name': name})

    def connect_network(self, container: str, network: str) -> None:
        self._post('/network/connect', {'container': container, 'network': network})

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------
    def _get_stream(self, path: str, params: dict = None, timeout: int = 300) -> requests.Response:
        headers = {k: v for k, v in self._headers.items() if k != 'Content-Type'}
        try:
            return requests.get(f'{self.base}{path}', headers=headers, params=params,
                                stream=True, timeout=timeout)
        except Exception as e:
            raise AgentError(str(e)) from e

    def list_downloads(self, container_name: str, download_path: str) -> list:
        data = self._get(f'/container/{container_name}/downloads', params={'download_path': download_path})
        return data.get('files', [])

    def get_download_stream(self, container_name: str, filename: str, download_path: str) -> requests.Response:
        return self._get_stream(f'/container/{container_name}/downloads/{filename}', params={'download_path': download_path})

    def upload_files(self, container_name: str, file_pairs: list, upload_path: str) -> list:
        headers = {'Authorization': self._headers['Authorization']}
        multipart = [('file[]', (name, data)) for name, data in file_pairs]
        try:
            r = requests.post(
                f'{self.base}/container/{container_name}/uploads',
                headers=headers,
                files=multipart,
                params={'upload_path': upload_path},
                timeout=300,
            )
            data = r.json()
        except Exception as e:
            raise AgentError(str(e)) from e
        if not data.get('ok'):
            raise AgentError(data.get('error', 'upload failed'))
        return data.get('names', [])

    # ------------------------------------------------------------------
    # Pull status
    # ------------------------------------------------------------------
    def get_pull_status(self, image: str) -> dict:
        try:
            return self._get('/image/pull/status', params={'image': image})
        except AgentError:
            return {"ok": True, "status": "unknown"}

    # ------------------------------------------------------------------
    # Prune
    # ------------------------------------------------------------------
    def prune_images(self, mode: str, app_image_set: set = None) -> int:
        data = self._post('/prune', {
            'mode': mode,
            'app_image_set': list(app_image_set or []),
        })
        return data.get('freed_bytes', 0)
