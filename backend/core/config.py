from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    APP_NAME: str = "TasAR"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    ENVIRONMENT: str = "development"
    # Solo dev/test: si es True, el lifespan crea el schema con create_all.
    # En prod queda OFF y el schema lo gobierna Alembic (WO F0-03).
    AUTO_CREATE_SCHEMA: bool = False
    PORT: int = 8600
    FRONTEND_URL: str = "http://localhost:5600"
    CORS_ORIGINS: str = '["http://localhost:5600"]'

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "TasAR"

    CLAUDE_CMD: str = "claude"
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # --- wa-gateway (WhatsApp / Baileys, WO F0-05) ---
    # URL base del wa-gateway (suite -> gateway, para el proxy de gestion).
    WA_GATEWAY_URL: str = ""
    # Secreto compartido gateway<->suite (X-API-Key). Vacio => wa-auth responde 503.
    WA_GATEWAY_KEY: str = ""

    # --- Audio full-duplex WhatsApp (WO F3-01) ---
    # Groq Whisper: transcripcion de notas de voz entrantes.
    GROQ_API_KEY: str = ""
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"
    # ElevenLabs: TTS de la respuesta saliente (voz GENERICA, sin clonado —
    # gate del dueno F3-01: nada de voice-clone). voice_id por workspace
    # (workspace_bot_config.voice_id) pisa este default global.
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_DEFAULT_VOICE_ID: str = ""
    ELEVENLABS_MODEL: str = "eleven_flash_v2_5"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return [self.CORS_ORIGINS]


settings = Settings()
