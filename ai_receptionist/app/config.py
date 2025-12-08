from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_ENV: str = "production"
    PORT: int = 8010
    HOST: str = "0.0.0.0"
    DOMAIN: str = "receptionist.lexmakesit.com"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    
    # Internal State
    APP_READY: bool = False
    MOCK_MODE: bool = False
    
    # Voice Pipeline Tester
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "S9NKLs1GeSTKzXd9D0Lf"
    ELEVENLABS_MODEL: str = "eleven_turbo_v2"
    CHEAP_TEST_MODE: bool = True
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()
