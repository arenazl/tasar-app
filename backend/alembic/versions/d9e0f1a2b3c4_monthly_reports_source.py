"""monthly_reports.source -- distingue seed (demo) de custom (agregado real) (WO F4-03)

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-10 22:30:00.000000

WO F4-03: POST /api/reports/custom agrega market_listings reales (mediana
USD/m2, counts por zona, top zonas) y persiste el resultado en
monthly_reports. Para no mezclar esos reportes reales con los 6 seed
(formula sintetica de seed_v2.py, regla dura 11) se agrega `source`:
'seed' (default, retrocompatible con las filas existentes) | 'custom'.
El frontend usa este campo para mostrar el badge [DEMO] en los reportes
seed y ocultarlo en los custom.

Columna aditiva, NOT NULL con DEFAULT server-side -> segura para backfill
de filas existentes sin downtime. Reversible.

NOTA (igual que c8d9e0f1a2b3): escrita a mano, no verificada con un
`alembic upgrade head` real contra MySQL (no hay MySQL en el entorno de
autoria). Aplicada al dev DB compartido via ALTER TABLE directo (mismo
patron que scripts/_attic/_migrate_v2.py) para no correr el CLI de Alembic
contra la Aiven compartida -- ver hallazgo en el reporte de este WO.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'monthly_reports',
        sa.Column('source', sa.String(length=20), nullable=False, server_default='seed'),
    )
    op.create_index(
        'ix_monthly_reports_source', 'monthly_reports', ['source'],
    )


def downgrade() -> None:
    op.drop_index('ix_monthly_reports_source', table_name='monthly_reports')
    op.drop_column('monthly_reports', 'source')
