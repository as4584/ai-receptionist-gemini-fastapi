#!/bin/bash
set -e

# Log start
echo "Starting deployment at $(date)"

# Navigate to the git root (where the sparse checkout is initialized)
cd /home/lex/antigravity_bundle/apps

# Pull latest changes for the portfolio folder
# Pull latest changes for the portfolio folder
echo "Pulling latest changes..."
git pull origin master

# Stay in apps directory where docker-compose.yml lives
# cd /home/lex/antigravity_bundle <--- REMOVED

# Rebuild and restart only the portfolio service
echo "Rebuilding portfolio_web..."
docker compose build --no-cache portfolio_web
docker compose up -d portfolio_web

# Rebuild and restart the Self-Healing Agent
echo "Rebuilding antigravity_agent..."
docker compose build --no-cache antigravity_agent
docker compose up -d antigravity_agent

# Cleanup unused images to save space
docker image prune -f

echo "Deployment complete at $(date)"
