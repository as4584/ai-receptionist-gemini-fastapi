
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LOG_FILE = "/app/logs/agent.log"

def parse_logs():
    services = {
        "AI Receptionist": {"status": "Unknown", "last_check": "-"},
        "Portfolio": {"status": "Unknown", "last_check": "-"},
        "Inventory Manager": {"status": "Unknown", "last_check": "-"},
        "Caddy Proxy": {"status": "Unknown", "last_check": "-"}
    }
    actions = []
    
    if not os.path.exists(LOG_FILE):
        return services, actions

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        
    # Process lines in reverse for latest status
    for line in reversed(lines):
        # 2025-12-11 04:26:46,640 - SelfHealingAgent - INFO - ✅ AI Receptionist: Healthy (OK, Latency: Latency: 0ms)
        if "✅" in line:
            parts = line.split("✅")[1].strip().split(":")
            name = parts[0].strip()
            # Handle potential extra colons in "Healthy" msg
            msg = ":".join(parts[1:]).strip()
            
            if name in services and services[name]["status"] == "Unknown":
                services[name]["status"] = "Healthy"
                services[name]["last_check"] = line.split(" - ")[0]
                services[name]["details"] = msg
        
        elif "❌" in line:
            parts = line.split("❌")[1].strip().split(":")
            # Special case for "(HTTP) Failed" etc in name
            name_part = parts[0].split("(")[0].strip()
            msg = ":".join(parts[1:]).strip()
            
            if name_part in services and services[name_part]["status"] == "Unknown":
                services[name_part]["status"] = "Unhealthy"
                services[name_part]["last_check"] = line.split(" - ")[0]
                services[name_part]["details"] = msg
                
        # Collect recent actions (restarts/rebuilds)
        if "Attempting to restart" in line or "Triggering REBUILD" in line:
            if len(actions) < 10:
                actions.append({
                    "timestamp": line.split(" - ")[0],
                    "message": line.split("- WARNING -")[1].strip()
                })

    return services, actions

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    services, actions = parse_logs()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "services": services,
        "actions": actions
    })
