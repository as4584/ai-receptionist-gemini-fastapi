import os
import sys
from twilio.rest import Client
from app.config import get_settings
from app.receptionist_agent import ReceptionistAgent
from app.utils.logger import app_logger
from app.diagnostics import diagnostics

async def run_all():
    """Run all startup checks. Raises exception if critical check fails."""
    app_logger.info("Running startup checks...")
    settings = get_settings()
    
    # 1. Check Env Vars
    required_vars = ["OPENAI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]
    for var in required_vars:
        if not getattr(settings, var):
            raise ValueError(f"Missing environment variable: {var}")
    app_logger.info("Environment variables verified")

    # 2. Check Twilio Connectivity
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.api.v2010.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
        app_logger.info("Twilio API connection verified")
        diagnostics.last_twilio_status = "connected"
    except Exception as e:
        diagnostics.last_twilio_status = "error"
        raise ConnectionError(f"Twilio connection failed: {e}")

    # 3. Check OpenAI Connectivity
    try:
        import requests
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"OpenAI API check failed: {response.text}")
        
        diagnostics.model_connection_status = True
        app_logger.info("OpenAI API connection verified")
    except Exception as e:
        app_logger.warning(f"OpenAI connection failed: {e}. Switching to MOCK MODE.")
        settings.MOCK_MODE = True
        diagnostics.model_connection_status = False
        # Do not raise error, allow app to start in mock mode
    
    # 4. Mark App Ready
    settings.APP_READY = True
    app_logger.info("All startup checks passed. App is READY.")
