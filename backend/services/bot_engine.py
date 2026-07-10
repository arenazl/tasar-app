"""Motor del bot WhatsApp (WO F2-03).

Porta el loop de function-calling probado en AgentFlow (whatsapp_bot.py) + lo
batallado de SalesBot (COMMON_RULES de naturalidad, rolling summary, fallback
enlatado, anti-loop de texto degenerado). TODO scoped al workspace de la
conversacion via `BotContext`.

Ensamblado del system prompt (orden estable, para cache implícita de Gemini):
  1. Intro del asistente
  2. KB del workspace renderizada desde DB (placeholders {campo} sobre las
     plantillas .md de backend/knowledge/) + FAQs activas
  3. COMMON_RULES (naturalidad, anti-repeticion, derivacion)
  4. Fecha/hora AR (UTC-3) — al final porque cambia cada minuto
  5. Memoria larga (rolling summary) + estado de la conversacion

Function-calling: máx 4 turnos. Fallback enlatado si Gemini no responde. El bot
NUNCA inventa datos: propiedades/precios salen de las tools.
"""
from __future__ import annotations

import logging
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import WaConversation
from models.message import WaMessage, DIRECTION_INBOUND, DIRECTION_OUTBOUND
from services.bot_rules import (
    COMMON_RULES, DERIVAR_TOKEN, ESPERAR_TOKEN, build_fecha_actual_context,
)
from services.bot_tools import BotContext, TOOL_DECLARATIONS, execute_tool
import services.gemini_service as gemini


log = logging.getLogger("tasar.bot_engine")

MAX_TOOL_TURNS = 4
HISTORY_LIMIT = 30
# Rolling summary: minimo de mensajes nuevos desde el ultimo resumen para re-resumir.
SUMMARY_THRESHOLD = 20

# Campos de bot_config que son placeholders {campo} de las plantillas del KB.
_KB_FIELDS = (
    "business_name", "business_description", "address", "zones", "phone", "email",
    "website", "services", "commissions_text", "differentials", "business_hours", "tone",
)

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
_RAW_TEMPLATES_CACHE: Optional[str] = None


SYSTEM_INTRO = (
    "Sos el asistente virtual oficial de la inmobiliaria. Respondés consultas de "
    "clientes por WhatsApp usando la BASE DE CONOCIMIENTO y las TOOLS disponibles. "
    "Tu objetivo es ayudar a buscar propiedades, coordinar visitas, estimar valores "
    "y captar leads, derivando a un asesor humano cuando corresponde."
)


def _read_raw_templates() -> str:
    """Concatena las plantillas .md del KB (con placeholders SIN renderizar).
    Se cachea a nivel modulo: los .md no cambian en runtime."""
    global _RAW_TEMPLATES_CACHE
    if _RAW_TEMPLATES_CACHE is not None:
        return _RAW_TEMPLATES_CACHE
    pieces: List[str] = []
    if _KNOWLEDGE_DIR.exists():
        for md in sorted(_KNOWLEDGE_DIR.glob("suite_*.md")):
            try:
                pieces.append(md.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                log.warning("no pude leer %s: %s", md, e)
    _RAW_TEMPLATES_CACHE = "\n\n".join(pieces)
    return _RAW_TEMPLATES_CACHE


def _business_name(bot_config: Any, ctx_name: str) -> str:
    bn = getattr(bot_config, "business_name", None) if bot_config else None
    return (bn or ctx_name or "la inmobiliaria").strip()


def render_message(template: Optional[str], negocio: str) -> str:
    """Reemplaza {negocio} en un mensaje editable (welcome/off_hours/derivation)."""
    if not template:
        return ""
    return template.replace("{negocio}", negocio)


async def _render_knowledge(ctx: BotContext) -> str:
    """Renderiza el KB del workspace: placeholders {campo} <- bot_config + FAQs activas.

    Reemplazo token-a-token (no str.format) para no romper ante llaves sueltas.
    """
    template = _read_raw_templates()
    cfg = ctx.bot_config
    rendered = template
    for field in _KB_FIELDS:
        val = (getattr(cfg, field, None) if cfg else None) or "[sin definir]"
        rendered = rendered.replace("{" + field + "}", str(val))

    # FAQs activas del workspace, por prioridad (mayor primero) — prioridad sobre KB.
    from models.bot_config import BotFaq
    faqs = (await ctx.db.execute(
        select(BotFaq)
        .where(BotFaq.workspace_id == ctx.workspace_id, BotFaq.is_active == True)  # noqa: E712
        .order_by(BotFaq.priority.desc(), BotFaq.id.asc())
    )).scalars().all()
    if faqs:
        block = ["### PREGUNTAS FRECUENTES (prioridad sobre el resto del conocimiento) ###", ""]
        for f in faqs:
            block.append(f"P: {f.question}\nR: {f.answer}\n")
        rendered += "\n\n" + "\n".join(block)
    return rendered


async def _build_system_instruction(ctx: BotContext, total_msgs: int) -> str:
    negocio = _business_name(ctx.bot_config, ctx.workspace_name)
    knowledge = await _render_knowledge(ctx)
    parts: List[str] = [
        f"{SYSTEM_INTRO}\nNombre del negocio: {negocio}.",
        "═══════════════════════════════════════════════\n"
        f"BASE DE CONOCIMIENTO DE {negocio.upper()}\n"
        "═══════════════════════════════════════════════\n"
        f"{knowledge}\n"
        "═══════════════════════════════════════════════",
        COMMON_RULES,
        build_fecha_actual_context(),
    ]

    # Memoria larga (rolling summary).
    if ctx.conversation.rolling_summary_md:
        parts.append(
            "═══════════════════════════════════════════════\n"
            "MEMORIA LARGA DE ESTA CONVERSACIÓN\n"
            "═══════════════════════════════════════════════\n"
            "Datos clave acumulados de turnos anteriores. Usalos como contexto; si el "
            "cliente ya te dio estos datos, no se los vuelvas a pedir.\n\n"
            f"{ctx.conversation.rolling_summary_md}\n"
            "═══════════════════════════════════════════════"
        )

    # Estado de la conversacion / primer contacto.
    if total_msgs > 0:
        parts.append(
            "ESTADO: esta conversación YA EMPEZÓ (" + str(total_msgs) + " mensajes). "
            "No te vuelvas a presentar ni saludes como si fuera la primera vez; continuá "
            "el hilo respondiendo al último mensaje."
        )
    else:
        welcome = render_message(getattr(ctx.bot_config, "welcome_message", None) if ctx.bot_config else None, negocio)
        if welcome:
            parts.append(
                "PRIMER CONTACTO: es el primer mensaje de esta persona. Si es un saludo "
                "genérico, presentate con este mensaje (podés adaptarlo levemente):\n"
                f"\"{welcome}\"\n"
                "Si hizo una pregunta puntual, respondela primero y luego presentate."
            )
    return "\n\n".join(parts)


def _historial_a_contents(historial: List[WaMessage], nuevo: WaMessage) -> List[Dict[str, Any]]:
    contents: List[Dict[str, Any]] = []
    for m in historial:
        role = "user" if m.direction == DIRECTION_INBOUND else "model"
        contents.append({"role": role, "parts": [{"text": m.content or ""}]})
    contents.append({"role": "user", "parts": [{"text": nuevo.content or ""}]})
    return contents


def _antiloop(text: str) -> str:
    """Corta texto degenerado (Gemini atorado repitiendo una frase N veces)."""
    if not text or len(text) < 30:
        return text
    for unit_len in range(5, 81):
        if unit_len * 3 > len(text):
            break
        unit = text[:unit_len]
        i = 0
        while text[i:i + unit_len] == unit:
            i += unit_len
            if i // unit_len >= 3:
                break
        if i // unit_len >= 3:
            return unit.rstrip()
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) > 20:
        top, top_freq = Counter(words).most_common(1)[0]
        if top_freq >= 10 and len(top) >= 3:
            return "Disculpá, se me trabó el mensaje. ¿Me repetís lo último?"
    return text


_FALLBACKS = [
    "Disculpá, tuve un problemita para procesar eso. ¿Me lo repetís?",
    "Perdón, se me cortó. ¿Me contás de nuevo qué estabas buscando?",
    "Uy, me quedé sin señal un segundo. ¿Qué me decías?",
]


async def _actualizar_resumen_si_necesario(ctx: BotContext) -> None:
    """Rolling summary liviano (portado de SalesBot resumen_conv, simplificado).

    Si hay >= SUMMARY_THRESHOLD mensajes nuevos desde el último resumen y hay
    mensajes viejos por fuera de la ventana detallada, los resume en bullets con
    Gemini y guarda rolling_summary_md + summary_up_to_message_id. Best-effort.
    """
    conv = ctx.conversation
    desde_id = conv.summary_up_to_message_id or 0
    nuevos = (await ctx.db.execute(
        select(func.count(WaMessage.id)).where(
            and_(WaMessage.conversation_id == conv.id, WaMessage.id > desde_id)
        )
    )).scalar() or 0
    if nuevos < SUMMARY_THRESHOLD:
        return

    total = (await ctx.db.execute(
        select(func.count(WaMessage.id)).where(WaMessage.conversation_id == conv.id)
    )).scalar() or 0
    if total <= HISTORY_LIMIT:
        return

    take = total - HISTORY_LIMIT
    rows = (await ctx.db.execute(
        select(WaMessage).where(WaMessage.conversation_id == conv.id)
        .order_by(WaMessage.created_at.asc(), WaMessage.id.asc()).limit(take)
    )).scalars().all()
    if not rows:
        return

    dialogo = "\n".join(
        f"{'Cliente' if m.direction == DIRECTION_INBOUND else 'Bot'}: {(m.content or '').strip()}"
        for m in rows if (m.content or "").strip()
    )
    if not dialogo.strip():
        return

    prompt = (
        "Resumí en bullets cortos los DATOS DUROS de esta conversación de WhatsApp "
        "(nombre, zona/barrio de interés, presupuesto, tipo de propiedad, decisiones "
        "tomadas, promesas del bot). No inventes nada que no esté. Máximo 12 bullets. "
        "Si no hay datos duros, devolvé '(sin datos duros)'.\n\n"
        f"Conversación:\n---\n{dialogo[:16000]}\n---\n\nResumen:"
    )
    try:
        resumen = await gemini.chat_complete(prompt, system="Sos un asistente que resume charlas.", workspace_id=ctx.workspace_id)
    except Exception as e:  # noqa: BLE001
        log.warning("rolling summary Gemini fallo (ignorado): %s", type(e).__name__)
        return
    resumen = (resumen or "").strip()
    if not resumen or "(sin datos duros" in resumen.lower() or resumen.startswith("[Gemini"):
        return
    conv.rolling_summary_md = resumen
    conv.summary_up_to_message_id = rows[-1].id
    await ctx.db.flush()


async def procesar_mensaje_entrante(
    ctx: BotContext, nuevo_mensaje: WaMessage,
) -> Tuple[Optional[str], str]:
    """Procesa un mensaje entrante con Gemini function-calling.

    Devuelve (texto_respuesta, accion). accion ∈ {'continuar', 'derivar', 'esperar_humano'}.
    Las tools (incl. derivar_a_humano) mutan la conversacion directamente; el webhook
    usa la accion para el envio al cliente (p.ej. mensaje de derivación configurado).
    """
    # Rolling summary (best-effort, antes de cargar el historial reciente).
    try:
        await _actualizar_resumen_si_necesario(ctx)
    except Exception as e:  # noqa: BLE001
        log.warning("rolling summary error (ignorado): %s", type(e).__name__)

    # Historial reciente (ASC), excluyendo el mensaje nuevo.
    rows = (await ctx.db.execute(
        select(WaMessage)
        .where(and_(WaMessage.conversation_id == ctx.conversation.id, WaMessage.id != nuevo_mensaje.id))
        .order_by(WaMessage.created_at.desc(), WaMessage.id.desc())
        .limit(HISTORY_LIMIT)
    )).scalars().all()
    historial = list(reversed(rows))
    total_msgs = len(historial)

    system_instruction = await _build_system_instruction(ctx, total_msgs)
    contents = _historial_a_contents(historial, nuevo_mensaje)

    derivar_via_tool = False
    part: Optional[Dict[str, Any]] = None

    for _ in range(MAX_TOOL_TURNS):
        part = await gemini.generate_with_tools(
            contents=contents,
            tools=TOOL_DECLARATIONS,
            system_instruction=system_instruction,
            workspace_id=ctx.workspace_id,
            max_tokens=1200,
        )
        if not part:
            break
        if "functionCall" in part:
            fc = part["functionCall"]
            name = fc.get("name", "")
            args = fc.get("args", {}) or {}
            log.info("[bot.tools] %s(%s)", name, args)
            result = await execute_tool(ctx, name, args)
            if name == "derivar_a_humano" and result.get("ok") and result.get("derivado"):
                derivar_via_tool = True
            contents.append({"role": "model", "parts": [{"functionCall": fc}]})
            contents.append({
                "role": "user",
                "parts": [{"functionResponse": {"name": name, "response": {"result": result}}}],
            })
            continue
        if "text" in part and part["text"]:
            break

    # Fallback enlatado si Gemini no dio texto (patron SalesBot: la app nunca queda muda).
    if not part or "text" not in part or not part["text"]:
        log.warning("[bot] fallback disparado conv=%s (part=%s)", ctx.conversation.id, bool(part))
        if derivar_via_tool:
            return (None, "derivar")
        return (random.choice(_FALLBACKS), "continuar")

    text = _antiloop(part["text"].strip())
    action = "continuar"
    if DERIVAR_TOKEN in text:
        text = text.replace(DERIVAR_TOKEN, "").strip()
        action = "derivar"
    if ESPERAR_TOKEN in text:
        text = text.replace(ESPERAR_TOKEN, "").strip()
        action = "esperar_humano"
    if derivar_via_tool:
        action = "derivar"
    return (text or None, action)
