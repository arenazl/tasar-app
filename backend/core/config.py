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

    # --- Meta Cloud API oficial (WO F3-02) ---
    # Token de sistema (Bearer) con acceso a TODOS los WABA de los workspaces
    # conectados por Meta (patron Tech Provider: un Business Manager agrupa los
    # numeros de varios workspaces). SOLO env/Secret Manager -- jamas en la DB
    # ni se expone al frontend. El ruteo por workspace es por
    # workspace_bot_config.meta_phone_number_id, NO por este token.
    META_ACCESS_TOKEN: str = ""
    # Verify token del handshake GET del webhook (hub.verify_token). Meta exige
    # un unico valor por URL de webhook registrada -> es GLOBAL al server, no
    # por workspace. SOLO env por la misma regla de credenciales.
    META_WEBHOOK_VERIFY_TOKEN: str = ""
    # App secret del Meta Developer App, usado para validar la firma
    # X-Hub-Signature-256 (HMAC-SHA256) de cada POST del webhook. SOLO env.
    META_APP_SECRET: str = ""
    # Master switch del handoff por coexistence (WO F3-02, canal Meta). Best
    # effort / NO verificado contra un webhook real -- ver services/meta_client.py
    # parse_echo(). Default ON (igual criterio que SalesBot/gupshup.py); se
    # puede apagar sin tocar codigo si el shape asumido da falsos positivos.
    COEX_HANDOFF_ENABLED: bool = True

    # --- Web Push (WO F3-03) ---
    # Par de claves VAPID (par de curva eliptica P-256) que identifican al
    # servidor ante los push services del browser (FCM/Mozilla/etc). SOLO
    # env/Secret Manager -- nunca en DB ni en el frontend salvo la PUBLIC key
    # (se expone via GET /api/push/vapid-public-key, es la mitad publica del
    # par por diseno del protocolo Web Push). Vacio => push_notif.notify_user
    # hace no-op (mismo patron fail-soft que SMTP en email_service).
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    # Contacto (mailto: o https:) que va en el claim VAPID `sub`, requerido
    # por el protocolo Web Push para que el push service pueda contactar al
    # operador ante abuso.
    VAPID_SUBJECT: str = "mailto:admin@tasar.local"

    # --- Cron interno (WO F3-03) ---
    # Secreto compartido para el scheduler externo (lo define Infra) que
    # dispara POST /api/cron/weekly-summary. Header `X-Cron-Key`. Vacio o
    # no coincide => 403 (fail-closed).
    CRON_KEY: str = ""

    # --- Knowledge Share Protocol (KSP v1.2, WO F5-01) ---
    # Las DOS claves fijas de los generadores (bloque `generadores` de
    # base-compartida/2-APPS-ENTRADAS.json). GET /api/knowledge-base y los
    # endpoints /api/tools/* aceptan CUALQUIERA de las dos (comparacion
    # time-safe acumulada sobre ambas, protocolo 5.1). Si NINGUNA esta
    # configurada => 503 (fail-closed, nunca se filtra el KB sin secret).
    KB_CLAVE_SALESBOT: str = ""
    KB_CLAVE_MEDIASTUDIO: str = ""
    # Workspace demo que alimenta los samples EN VIVO de `entities` y las
    # llamadas a `/api/tools/*` cuando el consumidor no pide un workspace
    # puntual (header X-KB-Workspace: slug). Requiere data real (scripts/
    # seed_demo.py crea "tasar-demo"); si el slug no existe, el KB degrada
    # esos bloques sin inventar datos (regla dura #11).
    KB_DEMO_WORKSPACE_SLUG: str = "tasar-demo"

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
