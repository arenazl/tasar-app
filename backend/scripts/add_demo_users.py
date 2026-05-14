"""Asegura que existan admin / supervisor / vendedor con el workspace tasar-demo.
Idempotente: crea el workspace si no existe, agrega/actualiza usuarios.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal, engine, Base
from core.security import hash_password
import models  # registra metadata
from models.workspace import Workspace
from models.user import User


USERS = [
    ("admin@tasar.demo", "admin123", "Lucas Admin", "admin", "MAT-1234"),
    ("supervisor@tasar.demo", "supervisor123", "Pato Supervisor", "supervisor", "MAT-5678"),
    ("vendedor@tasar.demo", "vendedor123", "BUEPROP Vendedor", "vendedor", None),
]


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        ws = (await db.execute(select(Workspace).where(Workspace.slug == "tasar-demo"))).scalar_one_or_none()
        if not ws:
            ws = Workspace(name="TasAR Demo", slug="tasar-demo", plan="pro")
            db.add(ws)
            await db.flush()
            print(f"workspace tasar-demo creado (id={ws.id})")
        for email, pwd, name, role, lic in USERS:
            u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if u:
                u.password_hash = hash_password(pwd)
                u.full_name = name
                u.role = role
                u.license_number = lic
                u.is_active = True
                print(f"actualizado: {email} ({role})")
            else:
                db.add(User(
                    workspace_id=ws.id, email=email,
                    password_hash=hash_password(pwd),
                    full_name=name, role=role, license_number=lic,
                ))
                print(f"creado: {email} ({role})")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
