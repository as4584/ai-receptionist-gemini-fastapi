
import time
import logging
import docker
import requests
import os
import subprocess
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
PROJECT_DIR = "/app/project"
CLEANUP_INTERVAL = 86400 # 24 Hours

# Service Map
SERVICES = {
    "portfolio": {
        "compose_service": "portfolio_web",
        "container_name": "portfolio_web",
        "url": "http://portfolio_web:8000/api/health",
        "label": "Portfolio",
        "critical": True
    },
    "inventory": {
        "compose_service": "inventory_manager",
        "container_name": "inventory_manager_app",
        "url": "http://inventory_manager_app:8010/health",
        "label": "Inventory Manager",
        "critical": False
    },
    "receptionist": {
        "compose_service": "ai_receptionist_app",
        "container_name": "ai_receptionist_app",
        "url": "http://ai_receptionist_app:8010/health",
        "label": "AI Receptionist",
        "critical": True,
        "metrics_url": "http://ai_receptionist_app:8010/metrics",
        "webhook_url": "http://ai_receptionist_app:8010/twilio/webhook"
    },
    "caddy": {
        "compose_service": "caddy",
        "container_name": "antigravity_caddy",
        "url": None,
        "label": "Caddy Proxy",
        "critical": True
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
    try:
        return client.containers.get(config["container_name"])
    except docker.errors.NotFound:
        pass
        
    try:
        filters = {"label": f"com.docker.compose.service={config['compose_service']}"}
        containers = client.containers.list(filters=filters)
        if containers:
            return containers[0]
    except Exception as e:
        logger.error(f"Error searching for {config['label']}: {e}")
        
    return None

def check_container_health(container):
    """Check if container is running and healthy"""
    if not container:
        return False, "Container Not Found"
        
    if container.status != "running":
        return False, f"Status is {container.status}"
    
    container.reload()
    state = container.attrs.get('State', {})
    health = state.get('Health', {})
    if health:
         status = health.get('Status')
         if status == "unhealthy":
             return False, "Docker Healthcheck: unhealthy"
             
    return True, "OK"

def check_http_health(url, method="GET"):
    if not url:
        return True, "No URL configured"
    try:
        if method == "POST":
             response = requests.post(url, timeout=10, headers={"Host": "localhost"})
        else:
             response = requests.get(url, timeout=10, headers={"Host": "localhost"})
             
        if 200 <= response.status_code < 300:
            return True, f"HTTP {response.status_code}"
        return False, f"HTTP {response.status_code}"
    except RequestException as e:
        return False, f"Connection Failed: {e}"

def check_receptionist_metrics(config):
    """Check AI voice latency and connectivity"""
    url = config.get("metrics_url")
    if not url:
        return True, "No Metrics URL"
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            model_connected = data.get("model_connected", False)
            avg_latency = data.get("avg_latency", 0)
            
            if not model_connected and data.get("active_calls", 0) > 0:
                 # Only critical if calls are active and model is down
                 return False, "Model Disconnected during active calls"
            
            # Warn on high latency
            if avg_latency > 2000:
                 return True, f"High Latency: {avg_latency:.0f}ms"
                 
            return True, f"Latency: {avg_latency:.0f}ms"
    except Exception as e:
        return False, f"Metrics Failed: {e}"
        
    return True, "Metrics OK"

def restart_container(container):
    try:
        logger.warning(f"Attempting to restart {container.name}...")
        container.restart()
        logger.info(f"Successfully restarted {container.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to restart container: {e}")
        return False

def rebuild_service(service_name):
    """Run docker compose build && up for a specific service"""
    logger.warning(f"Triggering REBUILD for {service_name}...")
    try:
        # We invoke docker-compose from the project dir
        cmd = ["docker-compose", "up", "-d", "--build", "--force-recreate", service_name]
        result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Rebuild Successful for {service_name}")
            return True
        else:
            logger.error(f"Rebuild Failed for {service_name}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Rebuild Exception: {e}")
        return False

def run_cleanup():
    logger.info("Running Daily Cleanup Job...")
    try:
        client.images.prune(filters={'dangling': True})
        logger.info("Pruned dangling images")
        # Could also run 'docker system prune -f' via subprocess
        subprocess.run(["docker", "system", "prune", "-f"], check=False)
        return True
    except Exception as e:
        logger.error(f"Cleanup Failed: {e}")
        return False

def main_loop():
    logger.info("Starting Antigravity Self-Healing Agent (Robust Mode)...")
    last_cleanup = time.time()
    
    while True:
        logger.info("--- Starting Health Check Cycle ---")
        
        # Daily Cleanup
        if time.time() - last_cleanup > CLEANUP_INTERVAL:
            run_cleanup()
            last_cleanup = time.time()

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
                    # If container missing, try rebuild/up
                    if not rebuild_service(config["compose_service"]):
                        logger.critical(f"Failed to revive {label}")
                continue

            # 2. HTTP Application Check
            if config["url"]:
                is_healthy, http_msg = check_http_health(config["url"])
                if not is_healthy:
                    logger.error(f"❌ {label} (HTTP) Failed: {http_msg}")
                    restart_container(container)
                    continue
            
            # 3. Specific Receptionist Checks
            if key == "receptionist":
                # Webhook Check
                is_hook_ok, hook_msg = check_http_health(config["webhook_url"], method="POST")
                if not is_hook_ok:
                     logger.error(f"❌ {label} (Webhook) Failed: {hook_msg}")
                     # Webhook failure might be app logic, restart app
                     restart_container(container)
                     continue
                
                # Metrics/Latency Check
                is_metrics_ok, metrics_msg = check_receptionist_metrics(config)
                if not is_metrics_ok:
                    logger.warning(f"⚠️ {label} Metrics Warning: {metrics_msg}")
                    # Don't restart immediately for latency/model status unless critical
                    
                logger.info(f"✅ {label}: Healthy ({status_msg}, Latency: {metrics_msg})")
                continue

            logger.info(f"✅ {label}: Healthy ({status_msg})")

        logger.info("Cycle Complete. Sleeping...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
