import asyncio
from fastapi import FastAPI, Request, Response, WebSocket, BackgroundTasks
from fastapi.responses import HTMLResponse
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from app.config import get_settings
from app.health import router as health_router
from app.startup_checks import run_all
from app.twilio_handler import handle_media_stream
from app.utils.logger import app_logger
from app.diagnostics import diagnostics

app = FastAPI(title="AI Receptionist Production")
app.include_router(health_router)

@app.on_event("startup")
async def startup_event():
    try:
        await run_all()
    except Exception as e:
        app_logger.critical(f"Startup checks failed: {e}")
        # We don't exit here to allow diagnostics endpoint to be reachable,
        # but APP_READY remains False so /health returns 503.
        diagnostics.record_error(e, "Startup")

@app.post("/twilio/webhook")
async def twilio_webhook(request: Request):
    """Handle incoming Twilio Voice webhook."""
    settings = get_settings()
    
    # 1. Validate Request (if configured)
    # In production, we MUST validate.
    # We need to reconstruct the URL as seen by Twilio (https://receptionist.lexmakesit.com/twilio/webhook)
    # Since we are behind Caddy, we trust X-Forwarded-Proto/Host
    
    try:
        form_data = await request.form()
        params = dict(form_data)
        
        # Construct URL
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("host", settings.DOMAIN)
        url = f"{proto}://{host}/twilio/webhook"
        
        signature = request.headers.get("x-twilio-signature", "")
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        
        if not validator.validate(url, params, signature):
            app_logger.warning(f"Invalid Twilio signature. URL: {url}")
            # For strict production: raise HTTPException(403, "Invalid signature")
            # But for debugging deployment, we log warning.
            pass

        # 2. Check App Readiness
        if not settings.APP_READY:
            app_logger.error("App not ready, returning fallback TwiML")
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Our AI receptionist is temporarily unavailable. Please try again shortly.</Say></Response>',
                media_type="application/xml"
            )

        # 3. Return TwiML to connect to Media Stream
        response = VoiceResponse()
        connect = Connect()
        # Use wss:// for secure websocket
        stream_url = f"wss://{settings.DOMAIN}/twilio/stream"
        connect.stream(url=stream_url)
        response.append(connect)
        
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        app_logger.error(f"Error in webhook: {e}")
        diagnostics.record_error(e, "Webhook")
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred. Please try again later.</Say></Response>',
            media_type="application/xml"
        )

@app.websocket("/twilio/stream")
async def websocket_endpoint(websocket: WebSocket):
    await handle_media_stream(websocket)

from app.web_handler import handle_web_stream

@app.get("/web-call", response_class=HTMLResponse)
async def web_call_page():
    """Serve the web call testing page."""
    with open("app/templates/web_call.html", "r") as f:
        return f.read()

@app.websocket("/web-stream")
async def web_websocket_endpoint(websocket: WebSocket):
    await handle_web_stream(websocket)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the dashboard page."""
    with open("app/templates/dashboard.html", "r") as f:
        return f.read()

@app.get("/metrics")
async def get_metrics():
    """Return metrics for the dashboard."""
    return diagnostics.get_state()
