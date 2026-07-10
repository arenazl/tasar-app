"""normalize user roles — vocabulario UNICO admin|supervisor|vendedor [fix transversal post F2-01]

Revision ID: f4a5b6c7d8e9
Revises: e6f7a8b9c0d1
Create Date: 2026-07-10 00:00:00.000000

Hallazgo F2-01: el plan del rework (WO F1-01 S2) decidio unificar los roles de
usuario en admin | supervisor | vendedor, pero el modelo User quedo con
default="tasador" y los usuarios/seed existentes usaban ese valor legacy de
TasAR. Consecuencia: el DMO (F2-01) y lo que viene (F2-02 pipeline por
vendedor, F4-05 equipo, bot con derivacion round-robin) no encontraban
usuarios con rol "vendedor" y los guards admin|supervisor excluian a los
"tasador".

Esta migracion de DATOS (no de schema) normaliza los valores existentes de
`users.role`:
  - tasador                  -> vendedor   (el agente que tasa/vende es el
                                             rol operativo base de la suite)
  - gerente / coordinador    -> supervisor (legado AgentFlow, por si quedo
                                             algun residual de datos portados)

NOTA (igual que las migraciones anteriores del rework): se escribio A MANO
porque NO hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic
contra la Aiven compartida. NO se verifico un `alembic upgrade head` real
contra MySQL -- queda para un entorno con MySQL (dev/Infra, etapa E1).

El downgrade es LOSSY a proposito: vendedor -> tasador es best-effort (no se
puede distinguir, tras el upgrade, qué filas eran originalmente "tasador" vs
"vendedor" nativo si ya existian ambas). Se documenta explicitamente aca para
que Infra no asuma que el downgrade es simetrico.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'vendedor' WHERE role = 'tasador'")
    op.execute("UPDATE users SET role = 'supervisor' WHERE role IN ('gerente', 'coordinador')")


def downgrade() -> None:
    # LOSSY a proposito (ver docstring): no hay forma de recuperar cuales
    # filas "vendedor"/"supervisor" eran originalmente tasador/gerente/
    # coordinador vs. ya nativas del vocabulario nuevo. Best-effort: revierte
    # TODOS los "vendedor" a "tasador" para preservar el comportamiento previo
    # a esta migracion (guards que esperaban "tasador"). No revierte
    # "supervisor" -> "gerente"/"coordinador" porque supervisor ya era parte
    # del vocabulario oficial ANTES de esta migracion (WO F1-01) y la mayoria
    # de esas filas nunca fueron gerente/coordinador.
    op.execute("UPDATE users SET role = 'tasador' WHERE role = 'vendedor'")
