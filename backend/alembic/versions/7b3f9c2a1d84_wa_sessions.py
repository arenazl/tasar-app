"""wa_sessions (auth-state key-value store del wa-gateway)

Revision ID: 7b3f9c2a1d84
Revises: 1e616292cc4e
Create Date: 2026-07-10 00:00:00.000000

Crea la tabla `wa_sessions`: key-value plano donde el wa-gateway (Baileys)
persiste el auth-state de cada tenant (workspace). Modelo:
backend/models/wa_session.py (WO F0-05).

NOTA (igual que la baseline 1e616292cc4e): esta migracion se escribio A MANO
porque NO hay un MySQL disponible en el entorno de autoria y esta PROHIBIDO
correr Alembic contra la Aiven compartida. El DDL usa tipos SQLAlchemy
genericos (String, Text, DateTime) validos para MySQL. NO se verifico un
`alembic upgrade head` real contra MySQL -- queda para un entorno con MySQL
(dev/Infra, etapa E1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3f9c2a1d84'
down_revision: Union[str, None] = '1e616292cc4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'wa_sessions',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('wa_sessions')
