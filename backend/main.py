from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import engine, Base
import models  # noqa: F401 — registra todos los modelos en Base.metadata

from api import (
    auth, properties, market_studies, appraisals,
    collaboration, ai, scraping, heatmap, dashboard, settings as settings_api,
    inbox, market, reports, ai_coach, clients,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
