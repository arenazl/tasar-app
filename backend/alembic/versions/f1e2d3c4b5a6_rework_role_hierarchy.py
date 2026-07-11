"""rework roles -> jerarquia del rubro inmobiliario broker|administrador|coordinador|asesor [WO F6-06]

Revision ID: f1e2d3c4b5a6
Revises: 32456ebf3597
Create Date: 2026-07-11 00:00:00.000000

Decision del dueno (WO F6-06): unificar el vocabulario de roles a la jerarquia
real de una inmobiliaria, 4 niveles:

    broker > administrador > coordinador > asesor

Es una sola app, un login; cada nivel hace TODAS las funciones (tasar, CRM,
chat, pipeline) con distinto ALCANCE. Reemplaza el vocabulario anterior
(admin | supervisor | vendedor, unificado en el fix 477dcc4).

Esta migracion es de DATOS (no de schema). Mapea los valores existentes de
`users.role`:
    admin      -> broker        (titular con matricula: acceso total)
    supervisor -> coordinador   (ve todo + gestiona lo comercial)
    vendedor   -> asesor        (opera lo suyo + lo sin asignar)

`administrador` (nivel 3) es un rol NUEVO: nadie lo tiene tras este mapeo; el
broker lo asigna a mano despues desde Equipo. Por eso NO se produce aca.

Idempotente: los UPDATE por valor exacto no re-tocan filas ya migradas (correr
dos veces no cambia nada). Los defaults de la columna quedan a nivel de modelo
(models/user.py: default="asesor"); no se toca el DDL.

NOTA (igual que el resto del rework): en el entorno de autoria NO hay MySQL y
esta PROHIBIDO correr Alembic contra la Aiven compartida, asi que este archivo
NO se aplico via `alembic upgrade`. En prod (unica base `tasar`) la migracion de
datos se aplico con un script directo idempotente (excepcion autorizada por el
dueno, WO F6-06), equivalente 1:1 a este upgrade(). Encadenado al head real
(32456ebf3597) para mantener una unica cabeza cuando Infra alinee Alembic.

Downgrade LOSSY a proposito: revierte broker/coordinador/asesor al vocabulario
anterior, pero los `administrador` (rol nuevo) se colapsan a `admin` (su
equivalente de "gestion plena") porque no existian antes del rework.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = '32456ebf3597'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'broker'      WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'coordinador' WHERE role = 'supervisor'")
    op.execute("UPDATE users SET role = 'asesor'      WHERE role = 'vendedor'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin'      WHERE role = 'broker'")
    # LOSSY: 'administrador' es un nivel nuevo sin equivalente 1:1 previo; se
    # colapsa a 'admin' (gestion plena) para no dejar un valor fuera del
    # vocabulario anterior.
    op.execute("UPDATE users SET role = 'admin'      WHERE role = 'administrador'")
    op.execute("UPDATE users SET role = 'supervisor' WHERE role = 'coordinador'")
    op.execute("UPDATE users SET role = 'vendedor'   WHERE role = 'asesor'")
