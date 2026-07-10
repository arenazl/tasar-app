"""WaSession — key-value store del auth-state de Baileys para el wa-gateway.

Espejo de AgentFlow/backend/models/baileys_auth.py (WO F0-05). El gateway
WhatsApp persiste aca cada archivo de auth de Baileys (creds, pre-key__N,
session__jid, app-state-sync-key__N, etc). Es un store PLANO key-value:
el namespacing por tenant vive en la propia key, prefijada con
`{workspace_slug}-` (ej `mi-agencia-creds`), asi que el modelo es agnostico
del workspace.

El value es el auth-state serializado por Baileys con BufferJSON (un JSON
string), por eso la columna es Text y no LargeBinary.
"""
from sqlalchemy import Column, String, Text, DateTime, func
from core.database import Base


class WaSession(Base):
    __tablename__ = "wa_sessions"

    # Key completa, ya prefijada por tenant (ej "mi-agencia-creds").
    key = Column(String(255), primary_key=True)
    # Auth-state serializado (BufferJSON -> JSON string).
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
