"""
System Health and Diagnostics Endpoints.
"""
import shutil
from fastapi import APIRouter, Depends
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import sounddevice as sd

from backend.app.core.database import get_db
from backend.app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    # 1. Database Check
    db_status = "UNKNOWN"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "HEALTHY"
    except Exception as e:
        db_status = f"UNHEALTHY ({e})"

    # 2. Ollama Status
    ollama_status = "UNKNOWN"
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                ollama_status = "HEALTHY"
                ollama_models = [m.get("name") for m in res.json().get("models", [])]
            else:
                ollama_status = f"HTTP_{res.status_code}"
    except Exception as e:
        ollama_status = f"OFFLINE ({e})"

    # 3. Audio Subsystem & Virtual Audio Cable Check
    audio_status = "DEGRADED"
    vac_found = False
    try:
        devices = sd.query_devices()
        for d in devices:
            if "virtual audio cable" in d["name"].lower() or "line 1" in d["name"].lower():
                vac_found = True
                break
        audio_status = "READY (Virtual Cable Active)" if vac_found else "READY (Hardware Default Only)"
    except Exception as e:
        audio_status = f"ERROR ({e})"

    # 4. Storage Disk Space
    disk = shutil.disk_usage(".")
    free_gb = round(disk.free / (1024**3), 2)

    return {
        "status": "HEALTHY" if db_status == "HEALTHY" and "HEALTHY" in ollama_status else "DEGRADED",
        "database": db_status,
        "ollama": {
            "status": ollama_status,
            "configured_model": settings.OLLAMA_MODEL,
            "available_models": ollama_models
        },
        "audio_subsystem": {
            "status": audio_status,
            "virtual_cable_detected": vac_found
        },
        "storage": {
            "free_space_gb": free_gb
        },
        "google_integration": {
            "dry_run": settings.GOOGLE_DRY_RUN,
            "configured": bool(settings.GOOGLE_CLIENT_ID)
        }
    }
