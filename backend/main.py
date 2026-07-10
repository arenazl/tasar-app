import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import engine, Base
import models  # noqa: F401 — registra todos los modelos en Base.metadata

log = logging.getLogger("tasar.main")

from api import (
    auth, properties, market_studies, appraisals,
    collaboration, ai, scraping, heatmap, dashboard, settings as settings_api,
    inbox, market, reports, ai_coach, clients, wa_auth, wa_gateway,
    valuations, coaches, dmo, visits, deals, authorizations,
    whatsapp, bot_config, conversations, meta, push, cron, team,
    knowledge_base,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El schema en prod lo gobierna Alembic (WO F0-03). create_all queda solo
    # para dev/test detras del flag AUTO_CREATE_SCHEMA (default off).
    if settings.AUTO_CREATE_SCHEMA:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.warning("AUTO_CREATE_SCHEMA=on -> create_all ejecutado (modo dev/test, NO usar en prod)")
    else:
        log.info("AUTO_CREATE_SCHEMA=off -> schema gobernado por Alembic (create_all salteado)")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(market_studies.router)
app.include_router(appraisals.router)
app.include_router(collaboration.router)
app.include_router(ai.router)
app.include_router(scraping.router)
app.include_router(heatmap.router)
app.include_router(dashboard.router)
app.include_router(settings_api.router)
app.include_router(inbox.router)
app.include_router(market.router)
app.include_router(reports.router)
app.include_router(ai_coach.router)
app.include_router(clients.router)
app.include_router(valuations.router)
# DMO (Daily Method of Operation, WO F2-01): catalogo global de coaches +
# templates/asignaciones/dia (scoping por workspace + roles).
app.include_router(coaches.router)
app.include_router(dmo.router)
# CRM: visitas, pipeline de ventas (deals) y autorizaciones (WO F2-02).
# Scoping por workspace + rol (vendedor ve lo suyo; supervisor/admin todo).
app.include_router(visits.router)
app.include_router(deals.router)
app.include_router(authorizations.router)
# wa-gateway (WhatsApp / Baileys, WO F0-05):
#   wa_auth   -> maquina-a-maquina (X-API-Key): /api/wa-auth/{key} + /api/wa/tenants
#   wa_gateway-> proxy JWT admin -> gateway: /api/wa/status|start|stop|qr.html
app.include_router(wa_auth.router)
app.include_router(wa_gateway.router)
# Bot WhatsApp embebido (WO F2-03):
#   whatsapp   -> webhook entrante Baileys (X-API-Key)
#   bot_config -> configuracion del bot POR WORKSPACE (JWT admin/supervisor)
app.include_router(whatsapp.router)
app.include_router(bot_config.router)
# Canal Meta Cloud API oficial (WO F3-02): webhook GET verify + POST incoming
# (HMAC X-Hub-Signature-256), ruteo por meta_phone_number_id. Mismo pipeline
# de procesamiento que Baileys (services/wa_inbound.py); envio unico por
# services/wa_out.py.
app.include_router(meta.router)
# Inbox humano de WhatsApp (WO F2-04): conversaciones (list sin N+1 + tomar mando +
# responder por gateway + reactivar bot), scoped por workspace + rol.
app.include_router(conversations.router)
# Web Push PWA (WO F3-03): subscribe/unsubscribe/test (JWT), cableado a los
# eventos de inbox_service (lead nuevo, derivacion, visita) via bot_tools.
app.include_router(push.router)
# Cron interno (WO F3-03): resumen semanal por email, X-Cron-Key -- el
# scheduler externo (Infra) lo dispara, este backend solo arma y despacha.
app.include_router(cron.router)
# Gestion de equipo (WO F4-05): miembros (ver/editar rol/desactivar) e
# invitaciones por email (invitar/reenviar/cancelar). Autorizacion por rol
# real (require_role): ver = admin/supervisor, gestionar = admin. El alta via
# token es publica y vive en auth.py.
app.include_router(team.router)
# Knowledge Share Protocol (WO F5-01): GET /api/knowledge-base(+/health) para
# SalesBot/Media Studio, protegido por X-KB-Key (KB_CLAVE_SALESBOT/
# KB_CLAVE_MEDIASTUDIO) -- ver base-compartida/3-PROTOCOLO-COMPLETO.md.
# Incluye /api/tools/* (tools function-calling reales del bot, publicadas en
# el KB con endpoint.path relativo).
app.include_router(knowledge_base.router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ok",
    }


@app.get("/api/health")
async def health():
    return {"ok": True}
