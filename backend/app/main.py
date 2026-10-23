"""
FastAPI Application Entry Point.
Configures CORS, middleware, API v1 routes, structured logging, and WebSocket Voice Room.
"""
import uuid
import time
import json
import base64
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import pyttsx3

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging
from backend.app.core.database import engine, Base
import backend.app.models # Register all models

# Import API Routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.tasks import router as tasks_router
from backend.app.api.v1.scheduling import router as scheduling_router
from backend.app.api.v1.meetings import router as meetings_router
from backend.app.api.v1.submissions import router as submissions_router
from backend.app.api.v1.reviews import router as reviews_router
from backend.app.api.v1.recordings import router as recordings_router
from backend.app.api.v1.notifications import router as notifications_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.benchmarks import router as benchmarks_router
from backend.app.api.v1.health import router as health_router

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    Path(settings.UPLOAD_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.RECORDING_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    logger.info("[STARTUP] Task Reviewer AI Backend initialized.")
    yield
    # Shutdown actions
    await engine.dispose()
    logger.info("[SHUTDOWN] Task Reviewer AI Backend terminated.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Internal company platform for automated task briefings, Google Meet reviews, and evidence-based evaluations.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID Middleware
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
    return response

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(tasks_router, prefix=api_v1_prefix)
app.include_router(scheduling_router, prefix=api_v1_prefix)
app.include_router(meetings_router, prefix=api_v1_prefix)
app.include_router(submissions_router, prefix=api_v1_prefix)
app.include_router(reviews_router, prefix=api_v1_prefix)
app.include_router(recordings_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(benchmarks_router, prefix=api_v1_prefix)
app.include_router(health_router, prefix=api_v1_prefix)

@app.get("/health")
async def root_health():
    return {"status": "healthy", "project": settings.PROJECT_NAME}

# Integrated WebSocket Voice Room endpoint
@app.websocket("/ws/voice-room/{meeting_id}")
async def websocket_voice_room(websocket: WebSocket, meeting_id: str):
    await websocket.accept()
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 165)

    async def speak_and_emit(sender: str, text: str):
        await websocket.send_json({"type": "transcript", "sender": sender, "text": text})
        out_wav = Path(settings.RECORDING_STORAGE_PATH) / f"ws_voice_{int(time.time()*1000)}.wav"
        tts_engine.save_to_file(text, str(out_wav))
        tts_engine.runAndWait()
        if out_wav.exists():
            with open(out_wav, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            await websocket.send_json({"type": "audio", "audio": b64})
            try:
                out_wav.unlink()
            except Exception:
                pass

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            m_type = data.get("type")

            if m_type == "consent":
                greeting = (
                    "Thank you for confirming recording consent. I am the Task Reviewer AI assistant. "
                    "I will guide your review session and answer questions regarding the approved requirements."
                )
                await speak_and_emit("Task Reviewer AI", greeting)

            elif m_type == "user_speech":
                speech_text = data.get("text", "")
                prompt = (
                    f"You are the Task Reviewer AI Assistant. The intern said: \"{speech_text}\". "
                    "Respond concisely in 1-2 spoken sentences. Be helpful, professional, and clear."
                )
                ai_reply = "I noted your points. Please verify that all deliverables meet the acceptance criteria."
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        res = await client.post(
                            f"{settings.OLLAMA_BASE_URL}/api/generate",
                            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
                        )
                        if res.status_code == 200:
                            ai_reply = res.json().get("response", "").strip()
                except Exception:
                    pass
                await speak_and_emit("Task Reviewer AI", ai_reply)

    except WebSocketDisconnect:
        logger.info(f"[VOICE ROOM] WebSocket disconnected for meeting {meeting_id}")

@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/api/v1/health"
    }
