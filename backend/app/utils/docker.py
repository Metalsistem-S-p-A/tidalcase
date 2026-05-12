import docker
import app.utils.agent_client
import app.models.tide
import app.utils.logger

def get_agent_client(agent):
    """Get or create a client for the given agent. Returns None on failure."""
    if agent.api_url and agent.api_token:
        return app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
    return None

def test_agent_connection(agent):
    """Test connection to an agent. Returns (success, message)."""
    if not agent.api_url or not agent.api_token:
        return False, "api_url and api_token are required"
    client = app.utils.agent_client.AgentHTTPClient(agent.api_url, agent.api_token)
    if client.ping():
        try:
            info = client.get_info()
            return True, f"Connected. Docker {info.get('docker_version', '?')}"
        except Exception:
            return True, "Connected."
    return False, "Connection failed"

def get_nginx_version():
    nginx_version = None
    try:
        nginx_container = docker.from_env().containers.get("tidalcase-nginx")
        result = nginx_container.exec_run("nginx -v")
        nginx_version = result.output.decode('utf-8').split("\n")[0].replace("nginx version: nginx/", "")
    except Exception:
        nginx_version = "Unable to get version"
    return nginx_version

def get_docker_version():
    docker_version = None
    try:
        docker_version = docker.from_env().version()["Version"]
    except Exception:
        docker_version = "Unable to get version"
    return docker_version

def list_available_networks():
    """List all available Docker networks"""
    try:
        networks = docker.from_env().networks.list()
        return [{"id": network.id, "name": network.name} for network in networks]
    except Exception as e:
        app.utils.logger.log("ERROR", f"Error listing networks: {str(e)}")
        return []
