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
    valuations, coaches, dmo,
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
# wa-gateway (WhatsApp / Baileys, WO F0-05):
#   wa_auth   -> maquina-a-maquina (X-API-Key): /api/wa-auth/{key} + /api/wa/tenants
#   wa_gateway-> proxy JWT admin -> gateway: /api/wa/status|start|stop|qr.html
app.include_router(wa_auth.router)
app.include_router(wa_gateway.router)


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
