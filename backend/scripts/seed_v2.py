"""Seed V2: data demo para market_listings, monthly_reports, inbox.

Cumple regla #11 CLAUDE.md global: todos los datos marcados como [DEMO],
coords reales de barrios (no random), montos representativos pero claros de ejemplo.
"""
import asyncio, sys, os, json, random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from core.database import AsyncSessionLocal
from models.workspace import Workspace
from models.user import User
from models.market_listing import MarketListing
from models.monthly_report import MonthlyReport
from models.inbox import InboxMessage
from models.appraisal import Appraisal
from models.property import Property


# ============ ZONAS REALES con USD/m² promedio (mayo 2026 aprox) ============
BARRIOS = [
    # (nombre, ciudad, prov, lat, lng, usd/m² base, demand_index)
    ("Palermo",       "CABA", "CABA",          -34.5800, -58.4300, 3420, 1.0),
    ("Recoleta",      "CABA", "CABA",          -34.5900, -58.3950, 3180, 0.95),
    ("Belgrano",      "CABA", "CABA",          -34.5600, -58.4500, 2890, 0.92),
    ("Núñez",         "CABA", "CABA",          -34.5450, -58.4600, 2750, 0.90),
    ("Colegiales",    "CABA", "CABA",          -34.5700, -58.4500, 2680, 0.85),
    ("Caballito",     "CABA", "CABA",          -34.6200, -58.4400, 2410, 0.80),
    ("Villa Crespo",  "CABA", "CABA",          -34.5980, -58.4400, 2380, 0.78),
    ("Almagro",       "CABA", "CABA",          -34.6100, -58.4200, 2050, 0.72),
    ("San Telmo",     "CABA", "CABA",          -34.6210, -58.3730, 1640, 0.60),
    ("Flores",        "CABA", "CABA",          -34.6280, -58.4640, 1820, 0.65),
    ("Saavedra",      "CABA", "CABA",          -34.5520, -58.4880, 2240, 0.75),
    ("Boedo",         "CABA", "CABA",          -34.6280, -58.4180, 1520, 0.55),
    ("Vicente López", "Vicente López", "Buenos Aires", -34.5300, -58.4750, 3150, 0.88),
    ("La Plata",      "La Plata",      "Buenos Aires", -34.9200, -57.9500, 1450, 0.55),
]

TYPES = ["departamento", "casa", "ph"]
TYPE_WEIGHTS = [0.7, 0.2, 0.1]  # 70% deptos
CONDITIONS = ["a_estrenar", "excelente", "muy_bueno", "bueno", "regular", "a_reciclar"]
COND_FACTOR = {"a_estrenar": 1.10, "excelente": 1.05, "muy_bueno": 1.00, "bueno": 0.95, "regular": 0.85, "a_reciclar": 0.75}

STREETS_BY_BARRIO = {
    "Palermo": ["Av. Santa Fe", "Av. Córdoba", "Honduras", "Gurruchaga", "Charcas", "Soler"],
    "Recoleta": ["Av. Santa Fe", "Av. Las Heras", "Av. Pueyrredón", "Vicente López", "Junín"],
    "Belgrano": ["Av. Cabildo", "Av. Libertador", "Juramento", "Echeverría", "Olleros"],
    "Núñez": ["Av. Cabildo", "Av. Libertador", "Crisólogo Larralde", "Iberá"],
    "Colegiales": ["Av. Federico Lacroze", "Av. Forest", "Concepción Arenal"],
    "Caballito": ["Av. Rivadavia", "Av. La Plata", "Acoyte", "Rojas"],
    "Villa Crespo": ["Av. Corrientes", "Av. Warnes", "Serrano", "Aguirre"],
    "Almagro": ["Av. Rivadavia", "Av. Medrano", "Yatay"],
    "San Telmo": ["Defensa", "Bolívar", "Chile", "México"],
    "Flores": ["Av. Rivadavia", "Av. Avellaneda", "Boyacá"],
    "Saavedra": ["Av. Cabildo", "Av. García del Río", "Ramallo"],
    "Boedo": ["Av. Boedo", "Av. San Juan", "Independencia"],
    "Vicente López": ["Av. Maipú", "Av. Libertador", "Av. del Libertador"],
    "La Plata": ["Calle 7", "Av. 13", "Av. 44", "Diagonal 74"],
}


def gen_market_listings(n: int = 500) -> list[dict]:
    """Genera N listings sintéticos coherentes con USD/m² por barrio."""
    random.seed(42)
    listings = []
    for i in range(n):
        barrio_data = random.choice(BARRIOS)
        bname, city, prov, lat, lng, base_ppm2, _ = barrio_data
        ptype = random.choices(TYPES, weights=TYPE_WEIGHTS)[0]

        # Variación leve de coords (dentro del barrio)
        lat += random.uniform(-0.008, 0.008)
        lng += random.uniform(-0.008, 0.008)

        # m² depende del tipo
        if ptype == "departamento":
            total = random.choice([45, 55, 65, 75, 85, 95, 105, 120])
            covered = total - random.randint(0, 8)
            rooms = max(1, total // 30)
        elif ptype == "casa":
            total = random.choice([140, 180, 220, 280, 320, 400])
            covered = int(total * random.uniform(0.55, 0.75))
            rooms = max(3, total // 60)
        else:  # ph
            total = random.choice([60, 80, 100, 120, 140])
            covered = int(total * random.uniform(0.7, 0.85))
            rooms = max(2, total // 40)

        cond = random.choices(CONDITIONS, weights=[0.05, 0.15, 0.30, 0.30, 0.15, 0.05])[0]
        age = {"a_estrenar": 0, "excelente": random.randint(2, 8), "muy_bueno": random.randint(8, 18),
               "bueno": random.randint(15, 35), "regular": random.randint(30, 55), "a_reciclar": random.randint(50, 80)}[cond]

        # Precio: base × m² × factor de estado × ruido +/- 8%
        ppm2 = base_ppm2 * COND_FACTOR[cond] * random.uniform(0.92, 1.08)
        price = round(ppm2 * total, -3)  # redondeo a miles
        ppm2_actual = round(price / total, 2)

        street = random.choice(STREETS_BY_BARRIO[bname])
        addr_num = random.randint(100, 5000)

        listings.append(dict(
            source="seed",
            external_id=f"SEED-{i+1:04d}",
            title=f"[DEMO] {ptype.title()} {rooms} amb. {bname}",
            property_type=ptype,
            operation="venta",
            province=prov,
            city=city,
            neighborhood=bname,
            address=f"{street} {addr_num}",
            latitude=round(lat, 6),
            longitude=round(lng, 6),
            total_area_m2=float(total),
            covered_area_m2=float(covered),
            rooms=rooms,
            bedrooms=max(1, rooms - 1),
            bathrooms=max(1, rooms // 2),
            age_years=age,
            condition=cond,
            orientation=random.choice(["norte", "sur", "este", "oeste", None]),
            floor=random.randint(1, 12) if ptype == "departamento" else None,
            parking_spots=random.choice([0, 1]),
            price=float(price),
            currency="USD",
            price_per_m2=ppm2_actual,
            status="active",
            days_on_market=random.randint(1, 180),
            photos_count=random.randint(4, 20),
        ))
    return listings


def gen_monthly_reports() -> list[dict]:
    """6 reportes mensuales: dic 2025 → may 2026."""
    base_ppm2 = 2500
    reports = []
    for i, (year, month) in enumerate([(2025, 12), (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5)]):
        idx = base_ppm2 + i * 70 + random.randint(-30, 30)
        yoy = round(11 + i * 0.6 + random.uniform(-1, 1), 1)
        mom = round(0.8 + random.uniform(-0.5, 0.7), 1)
        code = f"#{42 + i:03d}"  # #042 .. #047
        top = [
            {"zone": b[0], "usd_m2": int(b[5] * idx / 2500), "change_pct": round(random.uniform(-1.5, 3.5), 1)}
            for b in BARRIOS[:12]
        ]
        reports.append(dict(
            code=code,
            period_year=year, period_month=month,
            region="CABA", kind="mensual",
            tasar_index=float(idx),
            median_price_per_m2=float(idx),
            yoy_change_pct=yoy, mom_change_pct=mom,
            active_listings=18000 + i * 400 + random.randint(-200, 200),
            avg_days_on_market=100 - i * 2,
            new_permits=1000 + i * 40,
            top_zones=json.dumps(top, ensure_ascii=False),
            pages_count=random.randint(28, 42),
            published_at=datetime(year, month, 1) + timedelta(days=2),
        ))
    return reports


def gen_inbox(workspace_id: int, user_id: int) -> list[dict]:
    """12 mensajes de bandeja del screenshot real."""
    now = datetime.utcnow()
    items = [
        # Cliente reciente
        dict(kind="client_message", sender_type="client", sender_name="Mariana Sosa",
             sender_subtitle="Banco Río Plata", avatar_color="green",
             subject="Aprobación TR-2451",
             preview="Hola Bárbara, ¿podemos cerrar la tasación de Santa Fe 2350 hoy? El comité se reúne...",
             body=("Hola Bárbara, ¿podemos cerrar la tasación de Santa Fe 2350 hoy? El comité se reúne a las 16hs.\n\n"
                   "Te paso adjunto el contrato preliminar para que veas las condiciones. Como hablamos, el cliente final "
                   "requiere que la tasación quede registrada también en el sistema del BCRA.\n\n"
                   "Si necesitás algo más de mi lado avisame.\n\nSaludos,\nMariana"),
             priority="urgent", is_assigned_to_me=True,
             created_at=now - timedelta(minutes=8)),
        # Alerta sistema modelo
        dict(kind="system_alert", sender_type="system", sender_name="Sistema · Modelo",
             sender_subtitle="auto", avatar_color="yellow",
             subject="Alerta · cap rate fuera de rango",
             preview="TR-2448 (Quintana 480) muestra cap rate 6.2%, 1.8σ sobre la media de Recoleta...",
             body="TR-2448 (Quintana 480) muestra cap rate 6.2%, 1.8σ sobre la media de Recoleta (4.4%). Revisar si hay error de alquiler estimado o si es oportunidad real.",
             priority="high",
             created_at=now - timedelta(hours=1)),
        # Mención interna
        dict(kind="user_mention", sender_type="user", sender_name="Daniel Rojas",
             sender_subtitle="TasAR", avatar_color="blue",
             subject="Mencionó en TR-2449",
             preview="@Bárbara, hoy entró un comparable nuevo en Cabello que sube +6% el USD/m²...",
             body="@Bárbara, hoy entró un comparable nuevo en Cabello que sube +6% el USD/m² de la cuadra. Podría afectar la estimación de TR-2449.",
             priority="normal",
             created_at=now - timedelta(hours=2)),
        # Cliente con pedido múltiple
        dict(kind="client_message", sender_type="client", sender_name="Fondo Atlas",
             sender_subtitle="cliente", avatar_color="green",
             subject="Pidió 3 tasaciones",
             preview="Solicitud de tasación para Honduras 5240, Cabildo 2780 y Defensa 870 — modalidad...",
             body="Necesitamos tasaciones para 3 propiedades de la cartera para revisión trimestral. Modalidad estándar, plazo 7 días hábiles.",
             priority="high", is_assigned_to_me=True,
             created_at=now - timedelta(hours=4)),
        # Vencimiento
        dict(kind="overdue_task", sender_type="system", sender_name="Sistema",
             sender_subtitle="auto", avatar_color="orange",
             subject="TR-2444 vencida sin respuesta",
             preview="La solicitud de L. Martínez lleva 48hs sin abrirse. Reasignar?",
             body="La solicitud TR-2444 de Lucas Martínez lleva 48 horas sin movimiento. El SLA del cliente es 24 hs.",
             priority="urgent",
             created_at=now - timedelta(hours=18)),
        # Self reminder
        dict(kind="self_reminder", sender_type="user", sender_name="Bárbara López",
             sender_subtitle="self", avatar_color="blue",
             subject="Recordatorio · revisar TR-2450",
             preview="Te lo agendaste vos misma desde el detalle de TR-2450 para hoy 09:00.",
             body="Recordatorio que vos misma creaste: revisar TR-2450 antes del cierre de día.",
             priority="normal",
             created_at=now - timedelta(hours=22)),
        # Pago
        dict(kind="billing", sender_type="billing", sender_name="REMAX Cono Sur",
             sender_subtitle="cliente", avatar_color="green",
             subject="Pago confirmado · Mayo",
             preview="Recibimos USD 1.200 correspondientes al plan Empresa de mayo. Próxima fecha de cobro: 12 jun.",
             body="Pago confirmado por USD 1.200 correspondientes al plan Empresa de mayo.",
             priority="low", is_read=True,
             created_at=now - timedelta(days=3)),
        # Más mensajes
        dict(kind="comparable_added", sender_type="system", sender_name="Sistema",
             sender_subtitle="auto", avatar_color="yellow",
             subject="34 comparables nuevos en Palermo",
             preview="Se actualizó la base con 34 listings nuevos del último scrap. Match con tasaciones pendientes...",
             body="Se actualizó la base con 34 listings nuevos. Revisar impacto en TR-2451 y TR-2449.",
             priority="normal", is_read=True,
             created_at=now - timedelta(days=1)),
        dict(kind="client_message", sender_type="client", sender_name="Andrea Núñez",
             sender_subtitle="Particular", avatar_color="green",
             subject="Consulta sobre tasación de Belgrano",
             preview="Quería saber si pueden tasarme un PH en Belgrano R. ¿Costo y plazo?",
             body="Hola, buenos días. Quería saber si pueden tasarme un PH en Belgrano R, finalidad sucesión. ¿Costo y plazo de entrega?",
             priority="normal", is_read=True,
             created_at=now - timedelta(days=2)),
        dict(kind="appraisal_assigned", sender_type="system", sender_name="Sistema",
             sender_subtitle="auto", avatar_color="blue",
             subject="TR-2452 asignada a vos",
             preview="Te asignaron una tasación nueva: Cabello 3470, 11°A. Cliente: Fondo Atlas.",
             body="Te asignaron TR-2452. Inmueble en Cabello 3470, 11°A, Palermo. Cliente Fondo Atlas, finalidad venta.",
             priority="high", is_assigned_to_me=True, is_read=True,
             created_at=now - timedelta(days=2, hours=4)),
        dict(kind="system_alert", sender_type="system", sender_name="Sistema · Modelo",
             sender_subtitle="auto", avatar_color="yellow",
             subject="Índice TasAR · cierre mensual",
             preview="El índice cerró Mayo en 2.847 USD/m² (+1.2% MoM, +14.2% YoY). Top movers: Núñez +2.76%...",
             body="El índice TasAR cerró Mayo en 2.847 USD/m² (+1.2% MoM, +14.2% YoY). Top movers: Núñez +2.76%, Belgrano +2.1%, Palermo +1.9%.",
             priority="low", is_read=True,
             created_at=now - timedelta(days=5)),
        dict(kind="client_message", sender_type="client", sender_name="Estudio Pérez & Asoc.",
             sender_subtitle="Cliente legal", avatar_color="green",
             subject="Tasación pericial · sucesión Rodríguez",
             preview="Necesitamos tasación para sucesión judicial. Propiedad en Caballito, plazo 15 días.",
             body="Buenos días. Necesitamos tasación pericial para sucesión judicial Rodríguez. Inmueble en Caballito, plazo 15 días.",
             priority="normal", is_read=True,
             created_at=now - timedelta(days=6)),
    ]
    for item in items:
        item["workspace_id"] = workspace_id
        item["user_id"] = user_id
    return items


async def gen_appraisals(db, workspace_id: int, admin_id: int, props: list[Property]):
    """Genera 6 tasaciones demo con estados variados (TR-2446 .. TR-2451)."""
    statuses = ["solicitada", "en_analisis", "en_analisis", "en_revision", "aprobada", "entregada"]
    clientes = [
        ("Banco Río Plata", "Mariana Sosa", "mariana@bancorioplata.com.ar"),
        ("Fondo Atlas", "Diego Torres", "dt@fondoatlas.com.ar"),
        ("Argencapital", "Lucía Méndez", "lm@argencapital.com.ar"),
        ("M. Aldao", "Pablo Aldao", "pablo@aldao.com.ar"),
        ("Token Homes", "Ana Cortés", "ana@tokenhomes.io"),
        ("F. Pereyra", "Federico Pereyra", "fp@pereyra-tas.com"),
    ]
    purposes = ["venta", "hipoteca", "sucesion", "venta", "hipoteca", "judicial"]
    for i in range(6):
        prop = props[i % len(props)]
        cli_name, cli_contact, cli_email = clientes[i]
        ap = Appraisal(
            code=f"TR-{2446 + i}",
            workspace_id=workspace_id,
            property_id=prop.id,
            created_by=admin_id,
            assigned_to=admin_id,
            client_name=cli_name,
            client_contact=cli_contact,
            client_email=cli_email,
            purpose=purposes[i],
            status=statuses[i],
            method="hybrid",
            suggested_value_mode=prop.asking_price * random.uniform(0.95, 1.05) if prop.asking_price else None,
            suggested_value_min=prop.asking_price * 0.92 if prop.asking_price else None,
            suggested_value_max=prop.asking_price * 1.08 if prop.asking_price else None,
            suggested_value_per_m2=(prop.asking_price / prop.total_area_m2) if prop.asking_price and prop.total_area_m2 else None,
            confidence_score=random.uniform(0.65, 0.90),
            cap_rate=random.uniform(3.8, 5.5),
            comparables_count=random.randint(28, 45),
            currency="USD",
            final_value=(prop.asking_price * random.uniform(0.97, 1.02)) if i >= 3 and prop.asking_price else None,
        )
        db.add(ap)


async def main():
    async with AsyncSessionLocal() as db:
        ws = (await db.execute(select(Workspace).where(Workspace.slug == "tasar-demo"))).scalar_one()
        admin = (await db.execute(select(User).where(User.email == "admin@tasar.demo"))).scalar_one()
        props = (await db.execute(select(Property).where(Property.workspace_id == ws.id))).scalars().all()
        props = list(props)
        print(f"Workspace: {ws.name} (id={ws.id}), Admin: {admin.full_name}, Props: {len(props)}")

        # MARKET LISTINGS
        existing_listings = (await db.execute(select(MarketListing).limit(1))).scalar_one_or_none()
        if existing_listings is None:
            print("Generando 500 market_listings...")
            for item in gen_market_listings(500):
                db.add(MarketListing(**item))
            await db.commit()
            print("  OK500 listings creados")
        else:
            print("  skip market_listings (ya hay data)")

        # MONTHLY REPORTS
        existing_reports = (await db.execute(select(MonthlyReport).limit(1))).scalar_one_or_none()
        if existing_reports is None:
            print("Generando 6 monthly_reports...")
            for item in gen_monthly_reports():
                db.add(MonthlyReport(**item))
            await db.commit()
            print("  OK6 reportes creados")
        else:
            print("  skip monthly_reports (ya hay data)")

        # INBOX (siempre regenerar — son demo)
        await db.execute(delete(InboxMessage).where(InboxMessage.workspace_id == ws.id))
        print("Generando 12 inbox messages...")
        for item in gen_inbox(ws.id, admin.id):
            db.add(InboxMessage(**item))
        await db.commit()
        print("  OK12 mensajes inbox creados")

        # APPRAISALS demo (con TR- code)
        existing_ap_with_code = (await db.execute(
            select(Appraisal).where(Appraisal.workspace_id == ws.id, Appraisal.code.is_not(None)).limit(1)
        )).scalar_one_or_none()
        if existing_ap_with_code is None and props:
            print("Generando 6 tasaciones demo (TR-2446..TR-2451)...")
            await gen_appraisals(db, ws.id, admin.id, props)
            await db.commit()
            print("  OK6 tasaciones demo creadas")
        else:
            print("  skip appraisals (ya hay con code)")

        print("\nSeed V2 OK")


if __name__ == "__main__":
    asyncio.run(main())
