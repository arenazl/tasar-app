"""Verificacion standalone del bot WhatsApp (WO F2-03) — sin pytest, sin MySQL.

Usa una DB SQLite en memoria (aiosqlite) creada con Base.metadata.create_all, y
ejerce la LOGICA que NO depende del gateway ni de Gemini:

  [A] Round-robin scoped al workspace (nunca cruza tenants; orden por last_assigned_at).
  [B] Tools scoped al workspace (buscar/consultar no ven propiedades de otro workspace).
  [C] Idempotencia por meta_message_id (unique) + la query de dedup del webhook.
  [D] agendar_visita crea Client con origin='whatsapp' (sin error de enum) + Visit.
  [E] derivar_a_humano asigna round-robin, pausa el bot y setea assignee.

NO ejercita: el loop de Gemini function-calling, ni el envio real por el gateway
(no hay numero de test) — eso queda para un entorno con credenciales.

Uso:  python backend/scripts/test_bot_f2_03.py
Exit code 0 si todo PASA.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Satisfacer core.config antes de importar nada de la app (no conecta a MySQL).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import models  # noqa: F401 — registra metadata
from core.database import Base
from models.workspace import Workspace
from models.user import User
from models.property import Property
from models.conversation import WaConversation, STATUS_NUEVA
from models.message import WaMessage, DIRECTION_INBOUND
from services.bot_tools import (
    BotContext, asignar_round_robin, buscar_propiedades, consultar_propiedad,
    agendar_visita, derivar_a_humano, _phone_from_jid,
)


PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    status = PASS if cond else FAIL
    results.append(status)
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not cond else ""))


async def build_fixture(session: AsyncSession):
    wa = Workspace(name="Agencia A", slug="agencia-a", plan="free")
    wb = Workspace(name="Agencia B", slug="agencia-b", plan="free")
    session.add_all([wa, wb])
    await session.flush()

    # Vendedores de A: uno nunca asignado, uno asignado hace rato, uno no disponible.
    now = datetime.now(timezone.utc)
    v1 = User(workspace_id=wa.id, email="v1@a.com", password_hash="x", full_name="Vendedor Uno",
              role="vendedor", is_active=True, is_available=True, last_assigned_at=None, personal_phone="5491100000001")
    v2 = User(workspace_id=wa.id, email="v2@a.com", password_hash="x", full_name="Vendedor Dos",
              role="vendedor", is_active=True, is_available=True, last_assigned_at=now - timedelta(hours=1))
    v3 = User(workspace_id=wa.id, email="v3@a.com", password_hash="x", full_name="Vendedor Tres",
              role="vendedor", is_active=True, is_available=False)  # no disponible
    # Vendedor de B disponible (NO debe aparecer nunca en el round-robin de A).
    vb = User(workspace_id=wb.id, email="vb@b.com", password_hash="x", full_name="Vendedor B",
              role="vendedor", is_active=True, is_available=True, last_assigned_at=None)
    session.add_all([v1, v2, v3, vb])
    await session.flush()

    # Propiedades: A y B con la MISMA ciudad para probar que no se filtran cruzado.
    pa = Property(workspace_id=wa.id, created_by=v1.id, title="Depto A Palermo", property_type="departamento",
                  operation="venta", province="CABA", city="Palermo", address="Calle A 100",
                  rooms=3, asking_price=200000, currency="USD")
    pb = Property(workspace_id=wb.id, created_by=vb.id, title="Depto B Palermo", property_type="departamento",
                  operation="venta", province="CABA", city="Palermo", address="Calle B 200",
                  rooms=3, asking_price=210000, currency="USD")
    session.add_all([pa, pb])
    await session.flush()

    conv_a = WaConversation(workspace_id=wa.id, phone_jid="5491199999999@s.whatsapp.net",
                            contact_name="Cliente Test", status=STATUS_NUEVA, unread_count=0,
                            last_activity_at=now)
    session.add(conv_a)
    await session.flush()
    return {"wa": wa, "wb": wb, "v1": v1, "v2": v2, "v3": v3, "vb": vb, "pa": pa, "pb": pb, "conv_a": conv_a}


def ctx_for(session, fx):
    wa = fx["wa"]
    return BotContext(db=session, workspace_id=wa.id, workspace_slug=wa.slug,
                      workspace_name=wa.name, conversation=fx["conv_a"], bot_config=None, send=None)


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        fx = await build_fixture(session)
        await session.commit()

        # ── Pure helpers ──
        check("_phone_from_jid(@s.whatsapp.net)", _phone_from_jid("5491122334455@s.whatsapp.net") == "5491122334455")
        check("_phone_from_jid(@lid con :device)", _phone_from_jid("5491122334455:12@lid") == "5491122334455")

        # ── [A] round-robin scoped + orden ──
        chosen = await asignar_round_robin(session, fx["wa"].id)
        check("[A] round-robin elige v1 (nunca asignado, prioridad)", chosen is not None and chosen.id == fx["v1"].id,
              f"eligio {getattr(chosen,'email',None)}")
        check("[A] round-robin NO cruza workspace", chosen is not None and chosen.workspace_id == fx["wa"].id)
        # Simular que v1 recibio: ahora deberia elegir v2 (v3 no disponible).
        fx["v1"].last_assigned_at = datetime.now(timezone.utc)
        await session.flush()
        chosen2 = await asignar_round_robin(session, fx["wa"].id)
        check("[A] round-robin rota a v2 tras asignar v1", chosen2 is not None and chosen2.id == fx["v2"].id,
              f"eligio {getattr(chosen2,'email',None)}")
        # Workspace B: nunca devuelve un user de A.
        chosen_b = await asignar_round_robin(session, fx["wb"].id)
        check("[A] round-robin de B devuelve vendedor de B", chosen_b is not None and chosen_b.id == fx["vb"].id)

        ctx = ctx_for(session, fx)

        # ── [B] tools scoped al workspace ──
        res = await buscar_propiedades(ctx, zona="Palermo")
        ids = {p["id"] for p in res["propiedades"]}
        check("[B] buscar_propiedades solo ve propiedades del workspace A",
              ids == {fx["pa"].id}, f"ids={ids} (pb={fx['pb'].id} NO debe estar)")
        # consultar una propiedad de B desde el ctx de A -> not found.
        det_cross = await consultar_propiedad(ctx, fx["pb"].id)
        check("[B] consultar_propiedad de otro workspace -> not found", det_cross.get("ok") is False)
        det_own = await consultar_propiedad(ctx, fx["pa"].id)
        check("[B] consultar_propiedad propia -> ok", det_own.get("ok") is True)

        # ── [D] agendar_visita crea client origin='whatsapp' + visit ──
        vis = await agendar_visita(ctx, propiedad_id=fx["pa"].id,
                                   fecha_propuesta="2026-07-20T17:00:00-03:00", nombre_cliente="Juan")
        await session.flush()
        from models.client import Client
        from models.visit import Visit
        cli = (await session.execute(select(Client).where(Client.workspace_id == fx["wa"].id))).scalar_one_or_none()
        check("[D] agendar_visita ok", vis.get("ok") is True, str(vis))
        check("[D] client creado con origin='whatsapp' (sin error de enum)",
              cli is not None and cli.origin == "whatsapp")
        check("[D] client scoped al workspace A", cli is not None and cli.workspace_id == fx["wa"].id)
        v = (await session.execute(select(Visit).where(Visit.workspace_id == fx["wa"].id))).scalar_one_or_none()
        check("[D] visit creada agendada + scoped", v is not None and v.status == "agendada" and v.workspace_id == fx["wa"].id)

        # ── [E] derivar_a_humano asigna round-robin, pausa el bot, setea assignee ──
        conv = fx["conv_a"]
        conv.assignee_id = None
        conv.bot_paused_until = None
        await session.flush()
        der = await derivar_a_humano(ctx, motivo="cliente pidio asesor")
        await session.flush()
        check("[E] derivar_a_humano derivado=True", der.get("derivado") is True, str(der))
        check("[E] conversacion queda con assignee del workspace A",
              conv.assignee_id in {fx["v1"].id, fx["v2"].id})
        check("[E] bot pausado tras derivar", conv.bot_paused_until is not None)

        # ── [C] idempotencia meta_message_id (unique) ──
        session.add(WaMessage(conversation_id=conv.id, direction=DIRECTION_INBOUND,
                              content="hola", meta_message_id="MID-DUP-1"))
        await session.commit()
        # La query de dedup del webhook debe encontrarlo.
        dup = (await session.execute(select(WaMessage.id).where(WaMessage.meta_message_id == "MID-DUP-1"))).first()
        check("[C] dedup query encuentra el meta_message_id existente", dup is not None)
        # Insertar el mismo meta_message_id -> IntegrityError (unique).
        integrity_ok = False
        try:
            session.add(WaMessage(conversation_id=conv.id, direction=DIRECTION_INBOUND,
                                  content="hola de nuevo", meta_message_id="MID-DUP-1"))
            await session.commit()
        except IntegrityError:
            integrity_ok = True
            await session.rollback()
        check("[C] unique meta_message_id rechaza duplicado a nivel DB", integrity_ok)

    await engine.dispose()

    n_fail = results.count(FAIL)
    print(f"\n  RESULTADO: PASS={results.count(PASS)}  FAIL={n_fail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
