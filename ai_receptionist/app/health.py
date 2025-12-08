from fastapi import APIRouter, HTTPException
from app.config import get_settings
from app.diagnostics import diagnostics

router = APIRouter()

@router.get("/health")
async def health_check():
    settings = get_settings()
    if not settings.APP_READY:
        raise HTTPException(status_code=503, detail="App not ready")
        
    return {
        "ready": True,
        "uptime": diagnostics.get_uptime(),
        "last_error": diagnostics.last_error
    }

@router.get("/diagnostics")
async def get_diagnostics():
    return diagnostics.get_state()
