"""WorkspaceBotConfig + BotFaq — configuracion del bot POR WORKSPACE (WO F2-03).

Anti-patron a evitar (AgentFlow): BotConfig con `id=1` (singleton global). Aca la
config es 1 fila POR WORKSPACE (`workspace_id` unico). Prompt/KB/tools del bot se
arman siempre desde la fila del workspace de la conversacion.

- WorkspaceBotConfig: datos de negocio (placeholders {campo} del KB), mensajes
  editables (welcome/off_hours/derivacion), horario, palabras de derivacion, tono,
  y el flag `enabled` (si el bot atiende este workspace). SIN campos de "joda".
- BotFaq: preguntas/respuestas editables desde la app, con prioridad sobre el KB.

Los defaults (gate del dueno RESUELTO) viven como constantes aca para que tanto el
seed como el auto-create del endpoint usen exactamente los mismos textos. `{negocio}`
se reemplaza por el nombre del negocio (o del workspace) al renderizar.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func,
)
from core.database import Base


# ── Defaults del gate (rioplatense neutral/profesional) ────────────────────
DEFAULT_WELCOME = (
    "¡Hola! Gracias por escribir a {negocio}. Soy el asistente virtual: te puedo "
    "ayudar a buscar propiedades, coordinar una visita o darte una estimación de "
    "valor. ¿En qué te doy una mano?"
)
DEFAULT_OFF_HOURS = (
    "¡Hola! Ahora estamos fuera del horario de atención. Dejanos tu consulta y un "
    "asesor te responde apenas retomemos. Igual puedo ayudarte en este momento a "
    "buscar propiedades o agendar una visita."
)
DEFAULT_DERIVATION = (
    "Perfecto, te paso con un asesor del equipo que va a seguir tu consulta. En un "
    "ratito se comunica con vos. ¡Gracias por la paciencia!"
)
DEFAULT_DERIVATION_WORDS = (
    "hablar con una persona, con un humano, con un asesor, con alguien, atención "
    "humana, un vendedor, llamar por teléfono, reclamo, queja"
)
DEFAULT_TONE = "profesional"
DEFAULT_BUSINESS_HOURS = "Lunes a viernes de 9 a 18 hs. Sábados de 9 a 13 hs."
# Audio full-duplex (WO F3-01). off = nunca responde en audio (default seguro).
DEFAULT_VOICE_MODE = "off"


class WorkspaceBotConfig(Base):
    __tablename__ = "workspace_bot_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 1 fila por workspace (unico). NO singleton global.
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)

    # Interruptor: si el bot atiende este workspace. El gateway solo arranca sesion
    # para workspaces con el bot habilitado (ver /api/wa/tenants).
    enabled = Column(Boolean, default=False)

    # === Negocio (placeholders {campo} del KB) ===
    business_name = Column(String(200), nullable=True)
    business_description = Column(Text, nullable=True)
    address = Column(String(300), nullable=True)
    zones = Column(Text, nullable=True)            # zonas donde opera (texto libre / lista)
    phone = Column(String(60), nullable=True)
    email = Column(String(200), nullable=True)
    website = Column(String(200), nullable=True)
    services = Column(Text, nullable=True)         # servicios que ofrece
    commissions_text = Column(Text, nullable=True)
    differentials = Column(Text, nullable=True)    # diferenciales / por que elegirlos

    # === Mensajes editables ===
    welcome_message = Column(Text, nullable=True)
    off_hours_message = Column(Text, nullable=True)
    derivation_message = Column(Text, nullable=True)

    # === Horario / Derivacion ===
    business_hours = Column(Text, nullable=True)   # texto libre del horario de atencion
    derivation_words = Column(Text, nullable=True) # keywords de derivacion implicita
    tone = Column(String(30), default=DEFAULT_TONE)

    # === Conexion (el detalle Meta es de F3-02) ===
    channel_provider = Column(String(20), default="baileys")

    # === Audio full-duplex (WO F3-01) ===
    # Voz GENERICA de ElevenLabs para este workspace (gate del dueno: SIN
    # voice-clone). NULL => usa settings.ELEVENLABS_DEFAULT_VOICE_ID.
    voice_id = Column(String(80), nullable=True)
    # Default de voice_mode para conversaciones NUEVAS de este workspace
    # (off|auto|mirror). El override puntual vive en wa_conversations.voice_mode.
    default_voice_mode = Column(String(10), default=DEFAULT_VOICE_MODE)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BotFaq(Base):
    __tablename__ = "bot_faqs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    # Prioridad sobre el KB: mayor primero (se listan antes en el prompt).
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
