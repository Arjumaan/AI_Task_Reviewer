"""
Cartesia Neural Text-To-Speech (TTS) Service.
Integrates with api.cartesia.ai using model sonic-3.6 and custom voice IDs.
"""
import base64
import logging
from typing import Optional
import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class CartesiaTTSService:
    @classmethod
    async def synthesize_speech_bytes(
        cls,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesizes spoken natural audio bytes (MP3) for the given transcript text
        using Cartesia's Sonic neural TTS engine.
        """
        api_key = settings.CARTESIA_API_KEY
        target_voice = voice_id or settings.CARTESIA_VOICE_ID
        target_model = model_id or settings.CARTESIA_MODEL_ID or "sonic-3.6"

        if not api_key or not target_voice:
            logger.warning("[CARTESIA] Missing API key or Voice ID for speech synthesis.")
            return None

        cleaned_text = text.strip()
        if not cleaned_text:
            return None

        headers = {
            "X-API-Key": api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }

        payload = {
            "model_id": target_model,
            "transcript": cleaned_text,
            "voice": {
                "mode": "id",
                "id": target_voice
            },
            "language": "en",
            "output_format": {
                "container": "mp3",
                "sample_rate": 44100,
                "bit_rate": 128000
            },
            "generation_config": {
                "speed": 1.0,
                "volume": 1.0
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("https://api.cartesia.ai/tts/bytes", json=payload, headers=headers)
                if res.status_code == 200:
                    return res.content
                else:
                    logger.error(f"[CARTESIA ERROR] Status {res.status_code}: {res.text}")
                    return None
        except Exception as e:
            logger.error(f"[CARTESIA EXCEPTION] Failed to synthesize speech: {e}")
            return None

    @classmethod
    async def synthesize_speech_base64(
        cls,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Synthesizes audio bytes and returns a base64 encoded string ready for HTML5 Audio playback.
        """
        audio_bytes = await cls.synthesize_speech_bytes(text, voice_id, model_id)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
        return None
