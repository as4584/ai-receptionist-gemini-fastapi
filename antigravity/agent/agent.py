import time
import logging
import docker
import requests
import os
from requests.exceptions import RequestException

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/app/logs/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SelfHealingAgent")

# Configuration
DOCKER_SOCK = "unix://var/run/docker.sock"
CHECK_INTERVAL = 60
NETWORK_NAME = "antigravity_net"

# Service Map
SERVICES = {
    "portfolio": {
        "compose_service": "portfolio_web",
        "container_name": "portfolio_web",
        "url": "http://portfolio_web:8000/api/health",
        "label": "Portfolio"
    },
    "inventory": {
        "compose_service": "inventory_manager",
        "container_name": "inventory_manager_app",
        "url": "http://inventory_manager_app:8010/health",
        "label": "Inventory Manager"
    },
    "receptionist": {
        "compose_service": "ai_receptionist_app",
        "container_name": "ai_receptionist_app",
        "url": "http://ai_receptionist_app:8010/health",
        "label": "AI Receptionist"
    },
    "caddy": {
        "compose_service": "caddy",
        "container_name": "antigravity_caddy",
        "url": None,
        "label": "Caddy Proxy"
    }
}

try:
    client = docker.DockerClient(base_url=DOCKER_SOCK)
    logger.info("Connected to Docker Socket.")
except Exception as e:
    logger.critical(f"Failed to connect to Docker Socket: {e}")
    exit(1)

def get_container(config):
    """Resolve container by name or compose label"""
    # 1. Try Direct Name
    try:
        return client.containers.get(config["container_name"])
    except docker.errors.NotFound:
        pass
        
    # 2. Try Label Search
    try:
        filters = {"label": f"com.docker.compose.service={config['compose_service']}"}
        containers = client.containers.list(filters=filters)
        if containers:
            return containers[0] # Return valid container object
    except Exception as e:
        logger.error(f"Error searching for {config['label']}: {e}")
        
    return None

def check_container_health(container):
    """Check if container is running and healthy"""
    if not container:
        return False, "Container Not Found"
        
    if container.status != "running":
        return False, f"Status is {container.status}"
    
    # Check Docker Healthcheck if present
    # Reload attributes to get fresh status
    container.reload()
    state = container.attrs.get('State', {})
    health = state.get('Health', {})
    if health:
         status = health.get('Status')
         if status == "unhealthy":
             return False, "Docker Healthcheck: unhealthy"
             
    return True, "OK"

def check_http_health(url):
    if not url:
        return True, "No URL configured"
    try:
        # Send Host: localhost to pass TrustedHostMiddleware defaults
        response = requests.get(url, timeout=10, headers={"Host": "localhost"})
        # Portfolio returns 200, Receptionist returns 200
        if 200 <= response.status_code < 300:
            return True, f"HTTP {response.status_code}"
        return False, f"HTTP {response.status_code}"
    except RequestException as e:
        return False, f"Connection Failed: {e}"

def restart_container(container):
    try:
        logger.warning(f"Attempting to restart {container.name}...")
        container.restart()
        logger.info(f"Successfully restarted {container.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to restart container: {e}")
        return False
        
def restart_service_by_name(service_name):
    # Fallback if container object is missing (e.g. completely gone)
    # We can't restart a missing container object, we'd need to use 'docker compose up' 
    # But usually the container exists but is stopped.
    # If it's truly missing, we might need a different remediation.
    logger.error(f"Critical: Container for {service_name} is missing. Manual intervention or 'docker compose up' required.")
    # TODO: Implement 'docker compose up' remediation
    return False

def verify_network(network_name):
    try:
        networks = client.networks.list(names=[network_name])
        if not networks:
            logger.warning(f"Network {network_name} not found!")
            return False
        return True
    except Exception as e:
        logger.error(f"Error verifying network: {e}")
        return False

def main_loop():
    logger.info("Starting Antigravity Self-Healing Agent (Robust Mode)...")
    while True:
        logger.info("--- Starting Health Check Cycle ---")
        
        verify_network(NETWORK_NAME)
        
        for key, config in SERVICES.items():
            label = config["label"]
            container = get_container(config)
            
            # 1. Container Check
            is_running, status_msg = check_container_health(container)
            
            if not is_running:
                logger.error(f"❌ {label} (Container) Failed: {status_msg}")
                if container:
                    restart_container(container)
                else:
                    restart_service_by_name(key)
                continue

            # 2. HTTP Application Check
            if config["url"]:
                is_healthy, http_msg = check_http_health(config["url"])
                if not is_healthy:
                    logger.error(f"❌ {label} (HTTP) Failed: {http_msg}")
                    if container:
                        restart_container(container)
                else:
                    logger.info(f"✅ {label}: Healthy ({status_msg}, {http_msg})")
            else:
                 logger.info(f"✅ {label}: Healthy ({status_msg})")

        logger.info("Cycle Complete. Sleeping...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
