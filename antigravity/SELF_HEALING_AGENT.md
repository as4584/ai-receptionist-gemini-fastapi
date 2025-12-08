# Self-Healing Agent Specification

## 1. Overview
The Antigravity Self-Healing Agent is a background process designed to ensure the stability, security, and correctness of the unified Docker environment. It runs continuously to monitor container health, validate configurations, and automatically repair common issues.

## 2. Core Responsibilities

### A. Health Monitoring
- **Frequency**: Every 60 seconds.
- **Checks**:
    -   `docker ps` to ensure all expected containers (`portfolio_web`, `ai_receptionist_app`, `inventory_manager`, `caddy`, `db` services) are `Up`.
    -   `docker inspect --format '{{.State.Health.Status}}'` to verify `healthy` status for services with healthchecks.
    -   HTTP Healthchecks:
        -   Portfolio: `curl -f http://localhost:8001/health`
        -   Inventory: `curl -f http://localhost:8010/health`
        -   Receptionist: `curl -f http://localhost:8020/health`

### B. Configuration Validation
- **Frequency**: Every 5 minutes.
- **Checks**:
    -   Verify `docker-compose.yml` syntax using `docker compose config`.
    -   Check for broken symlinks in `/home/lex/antigravity_bundle/apps/`.
    -   Ensure `.env` file exists and contains required keys.

### C. Network & Routing Verification
- **Frequency**: Every 5 minutes.
- **Checks**:
    -   Verify `antigravity_net` exists.
    -   Verify Caddy is routing traffic correctly (e.g., `curl -H "Host: portfolio.internal" localhost`).

### D. Auto-Remediation (Self-Healing)
- **Trigger**: Health check failure.
- **Actions**:
    1.  **Restart Container**: `docker restart <container_name>`.
    2.  **Rebuild Service**: If restart fails twice, `docker compose up -d --force-recreate <service_name>`.
    3.  **Alerting**: Log failure and remediation attempt to `antigravity_bundle/logs/agent.log`.

## 3. Implementation Logic (Python Pseudo-code)

```python
def check_health():
    services = ["portfolio_web", "inventory_manager", "ai_receptionist_app", "caddy"]
    for service in services:
        status = get_container_status(service)
        if status != "running":
            log(f"{service} is down. Restarting...")
            restart_container(service)
        
        health = get_health_status(service)
        if health == "unhealthy":
            log(f"{service} is unhealthy. Restarting...")
            restart_container(service)

def verify_network():
    if not network_exists("antigravity_net"):
        create_network("antigravity_net")

def main_loop():
    while True:
        check_health()
        verify_network()
        sleep(60)
```

## 4. Deployment
The agent itself will be deployed as a container `antigravity_agent` within the master `docker-compose.yml`, mounting the Docker socket `/var/run/docker.sock` to perform management tasks.
