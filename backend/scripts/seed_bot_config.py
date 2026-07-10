"""Seed de la configuracion del bot POR WORKSPACE (WO F2-03).

Upsert de un WorkspaceBotConfig por workspace con los textos plantilla del gate del
dueño (RESUELTO). NO habilita el bot (enabled=False) — el dueño lo prende desde la
pantalla DatosIA cuando el canal esta conectado. Idempotente: no pisa configs ya
editadas (solo crea las que faltan).

Uso:
    python backend/scripts/seed_bot_config.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal
import models  # noqa: F401 — registra metadata
from models.workspace import Workspace
from models.bot_config import (
    WorkspaceBotConfig,
    DEFAULT_WELCOME, DEFAULT_OFF_HOURS, DEFAULT_DERIVATION,
    DEFAULT_DERIVATION_WORDS, DEFAULT_TONE, DEFAULT_BUSINESS_HOURS,
)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        workspaces = (await db.execute(select(Workspace).order_by(Workspace.id))).scalars().all()
        created = 0
        for ws in workspaces:
            existing = (await db.execute(
                select(WorkspaceBotConfig).where(WorkspaceBotConfig.workspace_id == ws.id)
            )).scalar_one_or_none()
            if existing:
                continue
            db.add(WorkspaceBotConfig(
                workspace_id=ws.id,
                enabled=False,
                business_name=ws.name,
                welcome_message=DEFAULT_WELCOME,
                off_hours_message=DEFAULT_OFF_HOURS,
                derivation_message=DEFAULT_DERIVATION,
                derivation_words=DEFAULT_DERIVATION_WORDS,
                business_hours=DEFAULT_BUSINESS_HOURS,
                tone=DEFAULT_TONE,
                channel_provider="baileys",
            ))
            created += 1
        await db.commit()
        print(f"[seed_bot_config] workspaces={len(workspaces)} config_creadas={created}")


if __name__ == "__main__":
    asyncio.run(main())
