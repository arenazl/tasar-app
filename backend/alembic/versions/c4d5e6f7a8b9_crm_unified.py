"""CRM unificado — visits/deals/authorizations + ampliacion clients/users/properties

Revision ID: c4d5e6f7a8b9
Revises: 7b3f9c2a1d84
Create Date: 2026-07-10 00:00:00.000000

WO F1-01: porta las entidades CRM de AgentFlow (clientes/visitas/pipeline_deals/
autorizaciones/users) sobre la base multi-tenant de TasAR. Tablas y columnas en
INGLES; toda tabla nueva lleva `workspace_id` (FK workspaces + indice). Modelos:
  backend/models/visit.py, deal.py, authorization.py  (nuevos)
  backend/models/client.py, user.py, property.py       (ampliados)

Esta migracion es UNICA para todo el paquete F1-01 y REVERSIBLE: `downgrade`
deshace exactamente lo que `upgrade` crea/altera.

NOTA (igual que baseline 1e616292cc4e y 7b3f9c2a1d84): se escribio A MANO porque
NO hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la
Aiven compartida. El DDL usa tipos SQLAlchemy genericos (Integer, String, Float,
Boolean, Date, DateTime, Text) validos para MySQL. NO se verifico un
`alembic upgrade head` real contra MySQL -- queda para un entorno con MySQL
(dev/Infra, etapa E1).

Ordenamiento MySQL-safe: en `downgrade` se dropea la FK ANTES del indice/columna
que sostiene, porque InnoDB no permite soltar una columna/indice referenciado
por una constraint FK viva.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = '7b3f9c2a1d84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 1) clients: ampliacion CRM / lead (portado de AgentFlow.clientes) ===
    op.add_column('clients', sa.Column('lead_status', sa.String(length=20), nullable=True))
    op.add_column('clients', sa.Column('temperature', sa.String(length=10), nullable=True))
    op.add_column('clients', sa.Column('origin', sa.String(length=20), nullable=True))
    op.add_column('clients', sa.Column('assigned_to', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('pref_zona', sa.String(length=150), nullable=True))
    op.add_column('clients', sa.Column('pref_m2_min', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('pref_m2_max', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('pref_ambientes', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('pref_budget_min', sa.Float(), nullable=True))
    op.add_column('clients', sa.Column('pref_budget_max', sa.Float(), nullable=True))
    op.add_column('clients', sa.Column('pref_currency', sa.String(length=5), nullable=True))
    op.add_column('clients', sa.Column('last_contact_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_clients_lead_status'), 'clients', ['lead_status'], unique=False)
    op.create_index(op.f('ix_clients_assigned_to'), 'clients', ['assigned_to'], unique=False)
    op.create_foreign_key('fk_clients_assigned_to_users', 'clients', 'users', ['assigned_to'], ['id'])

    # === 2) users: asignacion de leads / round-robin (portado de AgentFlow.users) ===
    op.add_column('users', sa.Column('is_available', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('last_assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('personal_phone', sa.String(length=40), nullable=True))
    op.add_column('users', sa.Column('daily_conversations_goal', sa.Integer(), nullable=True))

    # === 3) properties: captacion (portado de AgentFlow.propiedades) ===
    op.add_column('properties', sa.Column('captador_id', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('exclusivity', sa.Boolean(), nullable=True))
    op.create_index(op.f('ix_properties_captador_id'), 'properties', ['captador_id'], unique=False)
    op.create_foreign_key('fk_properties_captador_id_users', 'properties', 'users', ['captador_id'], ['id'])

    # === 4) visits (NUEVA, portado de AgentFlow.visitas) ===
    op.create_table(
        'visits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('voice_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_visits_workspace_id'), 'visits', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_visits_client_id'), 'visits', ['client_id'], unique=False)
    op.create_index(op.f('ix_visits_property_id'), 'visits', ['property_id'], unique=False)
    op.create_index(op.f('ix_visits_vendor_id'), 'visits', ['vendor_id'], unique=False)
    op.create_index(op.f('ix_visits_status'), 'visits', ['status'], unique=False)

    # === 5) deals (NUEVA, portado de AgentFlow.pipeline_deals) ===
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=True),
        sa.Column('negotiated_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=5), nullable=True),
        sa.Column('estimated_commission', sa.Float(), nullable=True),
        sa.Column('probability_pct', sa.Integer(), nullable=True),
        sa.Column('estimated_close_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deals_workspace_id'), 'deals', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_deals_client_id'), 'deals', ['client_id'], unique=False)
    op.create_index(op.f('ix_deals_property_id'), 'deals', ['property_id'], unique=False)
    op.create_index(op.f('ix_deals_vendor_id'), 'deals', ['vendor_id'], unique=False)
    op.create_index(op.f('ix_deals_stage'), 'deals', ['stage'], unique=False)

    # === 6) authorizations (NUEVA, portado de AgentFlow.autorizaciones) ===
    op.create_table(
        'authorizations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('captador_id', sa.Integer(), nullable=False),
        sa.Column('signed_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('min_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=5), nullable=True),
        sa.Column('commission_pct', sa.Float(), nullable=True),
        sa.Column('exclusivity', sa.Boolean(), nullable=True),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['captador_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_authorizations_workspace_id'), 'authorizations', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_authorizations_property_id'), 'authorizations', ['property_id'], unique=False)
    op.create_index(op.f('ix_authorizations_captador_id'), 'authorizations', ['captador_id'], unique=False)
    op.create_index(op.f('ix_authorizations_status'), 'authorizations', ['status'], unique=False)


def downgrade() -> None:
    # === 6) authorizations ===
    op.drop_index(op.f('ix_authorizations_status'), table_name='authorizations')
    op.drop_index(op.f('ix_authorizations_captador_id'), table_name='authorizations')
    op.drop_index(op.f('ix_authorizations_property_id'), table_name='authorizations')
    op.drop_index(op.f('ix_authorizations_workspace_id'), table_name='authorizations')
    op.drop_table('authorizations')

    # === 5) deals ===
    op.drop_index(op.f('ix_deals_stage'), table_name='deals')
    op.drop_index(op.f('ix_deals_vendor_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_property_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_client_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_workspace_id'), table_name='deals')
    op.drop_table('deals')

    # === 4) visits ===
    op.drop_index(op.f('ix_visits_status'), table_name='visits')
    op.drop_index(op.f('ix_visits_vendor_id'), table_name='visits')
    op.drop_index(op.f('ix_visits_property_id'), table_name='visits')
    op.drop_index(op.f('ix_visits_client_id'), table_name='visits')
    op.drop_index(op.f('ix_visits_workspace_id'), table_name='visits')
    op.drop_table('visits')

    # === 3) properties (FK antes que indice/columna) ===
    op.drop_constraint('fk_properties_captador_id_users', 'properties', type_='foreignkey')
    op.drop_index(op.f('ix_properties_captador_id'), table_name='properties')
    op.drop_column('properties', 'exclusivity')
    op.drop_column('properties', 'captador_id')

    # === 2) users ===
    op.drop_column('users', 'daily_conversations_goal')
    op.drop_column('users', 'personal_phone')
    op.drop_column('users', 'last_assigned_at')
    op.drop_column('users', 'is_available')

    # === 1) clients (FK antes que indice/columna) ===
    op.drop_constraint('fk_clients_assigned_to_users', 'clients', type_='foreignkey')
    op.drop_index(op.f('ix_clients_assigned_to'), table_name='clients')
    op.drop_index(op.f('ix_clients_lead_status'), table_name='clients')
    op.drop_column('clients', 'last_contact_at')
    op.drop_column('clients', 'pref_currency')
    op.drop_column('clients', 'pref_budget_max')
    op.drop_column('clients', 'pref_budget_min')
    op.drop_column('clients', 'pref_ambientes')
    op.drop_column('clients', 'pref_m2_max')
    op.drop_column('clients', 'pref_m2_min')
    op.drop_column('clients', 'pref_zona')
    op.drop_column('clients', 'assigned_to')
    op.drop_column('clients', 'origin')
    op.drop_column('clients', 'temperature')
    op.drop_column('clients', 'lead_status')
