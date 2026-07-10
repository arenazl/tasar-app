"""market_study cascade -- ondelete=CASCADE en comparables/adjustments (WO F3-05)

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-10 21:00:00.000000

WO F3-05: `delete_market_study` no borra comparables/adjustments hijos porque
no habia cascade -> IntegrityError con estudios cargados. El fix primario es
ORM-level (`cascade="all, delete-orphan"` en MarketStudy.comparables /
Comparable.adjustments, ver backend/models/market_study.py); esta migracion
agrega el `ON DELETE CASCADE` a nivel de FK como defensa en profundidad para
deletes que no pasen por el ORM (SQL directo, admin tooling, etc).

Las FK originales (`comparables.market_study_id` -> `market_studies.id` y
`adjustments.comparable_id` -> `comparables.id`) se crearon SIN nombre
explicito en la baseline (1e616292cc4e), asi que MySQL les asigno un nombre
autogenerado (tipicamente `<tabla>_ibfk_N`) que NO es fiable hardcodear.
Por eso el upgrade busca el nombre real via `Inspector.get_foreign_keys()`
en tiempo de ejecucion de la migracion, en vez de asumir un nombre fijo.

Migracion UNICA para F3-05 y REVERSIBLE.

NOTA (igual que las migraciones previas de la suite): escrita A MANO porque
NO hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra
la Aiven compartida. NO se verifico un `alembic upgrade head` real contra
MySQL -- queda para un entorno con MySQL (dev/Infra). La correctitud
funcional del cascade SI se verifico via fixture SQLite+ORM (independiente
de esta migracion, que solo endurece la FK a nivel DB).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_COMPARABLES = 'fk_comparables_market_study_id_market_studies'
FK_ADJUSTMENTS = 'fk_adjustments_comparable_id_comparables'


def _existing_fk_name(table: str, column: str, referred_table: str) -> str:
    """Ubica el nombre REAL (autogenerado por MySQL) de la FK `table.column`
    -> `referred_table.id`, en vez de asumir un nombre fijo tipo `_ibfk_N`."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get('constrained_columns') == [column] and fk.get('referred_table') == referred_table:
            return fk['name']
    raise RuntimeError(
        f"No se encontro la FK {table}.{column} -> {referred_table}.id "
        f"(esperada desde la baseline 1e616292cc4e)"
    )


def upgrade() -> None:
    old_name = _existing_fk_name('comparables', 'market_study_id', 'market_studies')
    op.drop_constraint(old_name, 'comparables', type_='foreignkey')
    op.create_foreign_key(
        FK_COMPARABLES, 'comparables', 'market_studies',
        ['market_study_id'], ['id'], ondelete='CASCADE',
    )

    old_name = _existing_fk_name('adjustments', 'comparable_id', 'comparables')
    op.drop_constraint(old_name, 'adjustments', type_='foreignkey')
    op.create_foreign_key(
        FK_ADJUSTMENTS, 'adjustments', 'comparables',
        ['comparable_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(FK_ADJUSTMENTS, 'adjustments', type_='foreignkey')
    op.create_foreign_key(None, 'adjustments', 'comparables', ['comparable_id'], ['id'])

    op.drop_constraint(FK_COMPARABLES, 'comparables', type_='foreignkey')
    op.create_foreign_key(None, 'comparables', 'market_studies', ['market_study_id'], ['id'])
