"""WhatsApp — webhook entrante Baileys (WO F2-03, audio F3-01).

UN solo webhook entrante (`POST /api/whatsapp/webhook/incoming`, auth X-API-Key ==
WA_GATEWAY_KEY, contrato de F0-05), scoped al workspace resuelto por el `tenant`
(slug) del payload.

Refactor WO F3-02 (canal Meta Cloud API oficial): el pipeline de procesamiento
(dedup, conversación, transcripción, coexistence, motor del bot, respuesta) es
COMÚN con el canal Meta y vive en `services/wa_inbound.process_incoming` — este
archivo ya NO lo duplica, solo valida la API key del gateway, resuelve el
workspace por `tenant` y le pasa el payload normalizado. El envío de la
respuesta pasa por `services/wa_out` (ÚNICO camino de salida, resuelve
baileys|meta por `workspace_bot_config.channel_provider`) — `_send_via_gateway`
se movió ahí tal cual como `wa_out._send_via_baileys`.

El inbox HUMANO (listar/ver/responder/tomar mando/reactivar) vive en
`api/conversations.py` (WO F2-04) y reutiliza `services/wa_out` + la constante
de pausa de coexistence (`services.wa_inbound.COEXISTENCE_PAUSE`).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.workspace import Workspace
from models.bot_config import WorkspaceBotConfig
from services.wa_inbound import IncomingPayload, process_incoming

log = logging.getLogger("tasar.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


def _check_gateway_key(x_api_key: Optional[str]) -> None:
    if not settings.WA_GATEWAY_KEY:
        raise HTTPException(503, "WA_GATEWAY_KEY no configurada")
    if x_api_key != settings.WA_GATEWAY_KEY:
        raise HTTPException(401, "API key invalida")


@router.post("/webhook/incoming")
async def webhook_incoming(
    payload: IncomingPayload,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_gateway_key(x_api_key)

    # Ruteo al workspace por slug (anti-cross-tenant).
    ws = (await db.execute(
        select(Workspace).where(Workspace.slug == payload.tenant)
    )).scalar_one_or_none()
    if not ws:
        raise HTTPException(404, f"Workspace (tenant) desconocido: {payload.tenant}")

    cfg = (await db.execute(
        select(WorkspaceBotConfig).where(WorkspaceBotConfig.workspace_id == ws.id)
    )).scalar_one_or_none()

    return await process_incoming(db, ws, cfg, payload)
