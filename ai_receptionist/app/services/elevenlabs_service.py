import requests
from app.config import get_settings
from app.utils.logger import app_logger

class ElevenLabsService:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.ELEVENLABS_API_KEY
        self.voice_id = self.settings.ELEVENLABS_VOICE_ID
        self.model = self.settings.ELEVENLABS_MODEL
        self.base_url = "https://api.elevenlabs.io/v1"

    def generate_audio(self, text: str) -> bytes:
        """Generate audio from text using ElevenLabs."""
        if not self.api_key or self.api_key == "placeholder_key_replace_me":
            app_logger.warning("ElevenLabs API key missing or invalid. Returning mock audio.")
            return b"mock_audio_data"

        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            app_logger.error(f"ElevenLabs generation failed: {e}")
            raise

    def validate_voice(self) -> dict:
        """Validate the voice configuration."""
        if not self.api_key or self.api_key == "placeholder_key_replace_me":
            return {"status": "failed", "error": "Missing API Key"}

        try:
            # Simple generation test
            audio = self.generate_audio("Hello")
            if len(audio) > 100:
                return {"status": "success", "latency": "unknown", "voice_id": self.voice_id}
            else:
                return {"status": "failed", "error": "Empty audio returned"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
