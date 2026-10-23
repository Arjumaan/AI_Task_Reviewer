"""
Application Configuration and Environment Settings.
Loads and validates settings using Pydantic Settings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Task Reviewer AI"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Security & JWT
    SECRET_KEY: str = "dev-secret-key-task-reviewer-ai-windows-local-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/reviewer.db"

    # Local AI & Models
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    OLLAMA_TIMEOUT_SECONDS: int = 45

    # Speech Services
    TTS_ENGINE: str = "pyttsx3"
    TTS_VOICE_PREFERENCE: str = "en_IN"
    STT_MODEL: str = "base.en"
    VIRTUAL_AUDIO_DEVICE: str = "Line 1 (Virtual Audio Cable)"

    # Storage Paths
    UPLOAD_STORAGE_PATH: str = "./storage/uploads"
    RECORDING_STORAGE_PATH: str = "./storage/recordings"
    RECORDING_RETENTION_DAYS: int = 90

    # Google Integrations
    GOOGLE_DRY_RUN: bool = True
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_REFRESH_TOKEN: Optional[str] = None

    # MeetingBaas Bot API
    MEETING_BAAS_API_KEY: str = "mb-iSMJYnSxRTyqMSXOzmimtcDoYtXewtDiEtkkwQYzNGIlJbJHGVlmjXuhiYfCT"
    MEETING_BAAS_BASE_URL: str = "https://api.meetingbaas.com/v2"
    MEETING_BAAS_SPEAKING_URL: str = "https://speaking.meetingbaas.com"
    MEETING_BAAS_WEBHOOK_URL: Optional[str] = None

    # Cartesia Neural TTS Voice
    CARTESIA_API_KEY: Optional[str] = "sk_car_KEA1mG2f5pGHkUDEFRBpjF"
    CARTESIA_VOICE_ID: str = "147f7727-7aa2-494c-993b-6178c79c7b6d"
    CARTESIA_MODEL_ID: str = "sonic-3.6"
    CARTESIA_VOICE_NAME: str = "Subha (Indian English)"

    # Review Engine Policies
    MAX_REVISION_ROUNDS: int = 3
    ENABLE_AUTONOMOUS_PASS: bool = True
    AUTO_RECORDING_CONSENT_REQUIRED: bool = True
    SANDBOX_EXECUTION_TIMEOUT_SECONDS: int = 10

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8765"
    ]

settings = Settings()
