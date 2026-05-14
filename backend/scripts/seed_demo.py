"""Seed demo: workspace + 3 usuarios + 12 propiedades en Argentina + price_history.

Cumple regla #11 del CLAUDE.md global: data marcada como [DEMO] / coords reales aproximadas
de barrios conocidos (Palermo, Recoleta, Belgrano, Núñez, Vicente López, La Plata, Córdoba, Rosario, Mendoza).
No usa random.uniform — usa coords reales de cada barrio.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal, engine, Base
from core.security import hash_password
import models  # registra metadata
from models.workspace import Workspace
from models.user import User
from models.property import Property
from models.price_history import PriceHistoryPoint


# Coordenadas reales aproximadas de barrios (no inventadas)
BARRIOS = {
    "Palermo, CABA": (-34.5800, -58.4300),
    "Recoleta, CABA": (-34.5900, -58.3950),
    "Belgrano, CABA": (-34.5600, -58.4500),
    "Núñez, CABA": (-34.5450, -58.4600),
    "Caballito, CABA": (-34.6200, -58.4400),
    "Vicente López, Bs As": (-34.5300, -58.4750),
    "La Plata, Bs As": (-34.9200, -57.9500),
    "Córdoba Capital": (-31.4200, -64.1880),
    "Rosario, Santa Fe": (-32.9500, -60.6400),
    "Mendoza Capital": (-32.8900, -68.8450),
}


PROPERTIES_SEED = [
    ("[DEMO] Departamento 3 amb. moderno", "departamento", "CABA", "Palermo, CABA", "Av. Santa Fe 3000", 95, 80, 3, 2, 1, 5, "excelente", 220000),
    ("[DEMO] PH al frente con patio", "ph", "CABA", "Caballito, CABA", "Av. Rivadavia 5400", 110, 95, 4, 3, 2, 25, "muy_bueno", 180000),
    ("[DEMO] Loft monoambiente Recoleta", "departamento", "CABA", "Recoleta, CABA", "Av. Las Heras 2800", 45, 42, 1, 1, 1, 8, "excelente", 145000),
    ("[DEMO] Casa Núñez 4 amb.", "casa", "CABA", "Núñez, CABA", "Av. Cabildo 4500", 220, 180, 5, 3, 3, 40, "bueno", 480000),
    ("[DEMO] Depto Belgrano R", "departamento", "CABA", "Belgrano, CABA", "Av. Cabildo 2900", 70, 65, 2, 1, 1, 15, "muy_bueno", 165000),
    ("[DEMO] Casa con quincho VL", "casa", "Buenos Aires", "Vicente López, Bs As", "Av. Maipú 1200", 320, 240, 6, 4, 3, 35, "muy_bueno", 520000),
    ("[DEMO] Depto a estrenar La Plata", "departamento", "Buenos Aires", "La Plata, Bs As", "Calle 12 e/47 y 48", 80, 75, 3, 2, 2, 0, "a_estrenar", 145000),
    ("[DEMO] Casa en Nueva Córdoba", "casa", "Córdoba", "Córdoba Capital", "Bv. Chacabuco 900", 180, 150, 5, 3, 2, 30, "bueno", 215000),
    ("[DEMO] Depto vista río Rosario", "departamento", "Santa Fe", "Rosario, Santa Fe", "Bv. Oroño 200", 105, 92, 3, 2, 2, 12, "excelente", 178000),
    ("[DEMO] Casa quinta Mendoza", "casa", "Mendoza", "Mendoza Capital", "Av. San Martín 500", 280, 200, 5, 4, 3, 20, "muy_bueno", 295000),
    ("[DEMO] Local comercial Palermo", "local", "CABA", "Palermo, CABA", "Av. Córdoba 4400", 65, 65, 1, 0, 1, 30, "bueno", 195000),
    ("[DEMO] Terreno suburbano", "terreno", "Buenos Aires", "Vicente López, Bs As", "Av. del Libertador 6500", 450, 0, None, None, None, None, None, 350000),
]


async def main():
    # Crear tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Workspace demo
        existing = (await db.execute(select(Workspace).where(Workspace.slug == "tasar-demo"))).scalar_one_or_none()
        if existing:
            print("Seed ya aplicado (workspace tasar-demo existe).")
            return

        ws = Workspace(name="TasAR Demo", slug="tasar-demo", plan="pro")
        db.add(ws)
        await db.flush()

        # Usuarios demo (admin, supervisor, vendedor)
        users = [
            User(workspace_id=ws.id, email="admin@tasar.demo",
                 password_hash=hash_password("admin123"),
                 full_name="Lucas Admin", role="admin", license_number="MAT-1234"),
            User(workspace_id=ws.id, email="supervisor@tasar.demo",
                 password_hash=hash_password("supervisor123"),
                 full_name="Pato Supervisor", role="supervisor", license_number="MAT-5678"),
            User(workspace_id=ws.id, email="vendedor@tasar.demo",
                 password_hash=hash_password("vendedor123"),
                 full_name="BUEPROP Vendedor", role="vendedor"),
        ]
        for u in users:
            db.add(u)
        await db.flush()
        admin = users[0]

        # Propiedades
        for title, ptype, prov, barrio_key, address, total, covered, rooms, beds, baths, age, cond, price in PROPERTIES_SEED:
            lat, lng = BARRIOS[barrio_key]
            city = barrio_key.split(",")[0].strip()
            neigh = city
            p = Property(
                workspace_id=ws.id, created_by=admin.id,
                title=title, property_type=ptype, operation="venta",
                province=prov, city=city, neighborhood=neigh, address=address,
                latitude=lat, longitude=lng,
                total_area_m2=total, covered_area_m2=covered,
                rooms=rooms, bedrooms=beds, bathrooms=baths,
                age_years=age, condition=cond,
                asking_price=price, currency="USD",
                description=f"Propiedad demo en {barrio_key}",
            )
            db.add(p)

            # Snapshot price history
            if price and total:
                db.add(PriceHistoryPoint(
                    workspace_id=ws.id,
                    province=prov, city=city, neighborhood=neigh,
                    property_type=ptype, operation="venta",
                    latitude=lat, longitude=lng,
                    price_per_m2=round(price / total, 2),
                    sample_size=1, source="manual",
                ))

        await db.commit()
        print(f"Seed OK — workspace 'tasar-demo' + {len(users)} users + {len(PROPERTIES_SEED)} props")
        print("Logins:")
        print("  admin@tasar.demo / admin123")
        print("  supervisor@tasar.demo / supervisor123")
        print("  vendedor@tasar.demo / vendedor123")


if __name__ == "__main__":
    asyncio.run(main())
