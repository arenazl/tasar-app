"""DMO — Daily Method of Operation (portado de AgentFlow, WO F2-01).

El DMO es la rutina diaria del vendedor: un template (metodologia) partido en
bloques horarios, donde cada bloque puede exigir una metrica (checkbox o
cantidad) y marcarse como "money block" (no negociable). El vendedor registra
su avance del dia (`DmoLog`) y la app calcula el % de completitud.

Portado desde `AgentFlow/backend/models/dmo.py` (castellano) al esquema de la
suite (INGLES + multi-tenant). Mapeo de nombres castellano -> ingles:

  Coach.nombre                     -> Coach.name
  Coach.descripcion                -> Coach.description
  Coach.foto_url                   -> Coach.photo_url
  Coach.fuente_url                 -> Coach.source_url
  Coach.es_oficial                 -> Coach.is_official
  DmoTemplate.nombre               -> DmoTemplate.name
  DmoTemplate.descripcion          -> DmoTemplate.description
  DmoTemplate.mercado              -> DmoTemplate.market
  DmoTemplate.activo               -> DmoTemplate.is_active
  DmoTemplate.es_default_inmobiliaria -> DmoTemplate.is_office_default
  DmoBloque (tabla)                -> DmoBlock (dmo_blocks)
  DmoBloque.hora_inicio            -> DmoBlock.start_time
  DmoBloque.hora_fin               -> DmoBlock.end_time
  DmoBloque.orden                  -> DmoBlock.sort_order
  DmoBloque.es_money_block         -> DmoBlock.is_money_block
  DmoBloque.metrica_tipo           -> DmoBlock.metric_type
  DmoBloque.metrica_label          -> DmoBlock.metric_label
  DmoBloque.metrica_meta           -> DmoBlock.metric_goal
  VendedorDmoAssignment (tabla)    -> DmoAssignment (dmo_assignments)
  VendedorDmoAssignment.vendedor_id-> DmoAssignment.vendor_id
  DmoLog.fecha                     -> DmoLog.date
  DmoLog.bloque_id                 -> DmoLog.block_id
  DmoLog.completado                -> DmoLog.completed
  DmoLog.valor_metrica             -> DmoLog.metric_value
  DmoLog.notas                     -> DmoLog.notes
  MetricaTipo.cantidad             -> metric_type == "quantity"

Convencion de la casa (ver models/client.py): los campos "enum" se guardan como
String con un comentario que lista los valores validos (NO se usa SAEnum como en
AgentFlow), para mantener el DDL portable a MySQL sin tipos ENUM nativos.

Multi-tenant (WO F2-01):
  - `coaches` es CATALOGO GLOBAL (sin workspace_id): las metodologias oficiales
    (Tom Ferry, Buffini, etc.) son compartidas por todos los tenants.
  - `dmo_templates.workspace_id` es NULLABLE: NULL = template oficial del catalogo
    global; con workspace = template custom del tenant (el clone copia
    oficial -> workspace). El resto de las tablas llevan workspace_id NOT NULL.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Time, Text,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


# metric_type: valores validos -> "checkbox" | "quantity"
METRIC_TYPE_CHECKBOX = "checkbox"
METRIC_TYPE_QUANTITY = "quantity"


class Coach(Base):
    """Autor / metodologia detras de un DMO (Tom Ferry, Buffini, Workman, custom).

    CATALOGO GLOBAL: sin workspace_id, compartido por todos los tenants. Los
    coaches `is_official=True` NO se pueden eliminar desde la API.
    """
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    is_official = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    templates = relationship("DmoTemplate", back_populates="coach")


class DmoTemplate(Base):
    """Un DMO concreto (puede haber varios por coach).

    `workspace_id` NULLABLE: NULL = template oficial del catalogo global;
    con workspace = template custom del tenant.
    """
    __tablename__ = "dmo_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # NULL = catalogo oficial global; set = custom del tenant.
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    market = Column(String(40), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # Default de la oficina (por workspace): el que se usa cuando un vendedor no
    # tiene asignacion explicita. Unico por workspace (lo garantiza el endpoint).
    is_office_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coach = relationship("Coach", back_populates="templates", lazy="joined")
    blocks = relationship(
        "DmoBlock",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="DmoBlock.sort_order",
    )


class DmoBlock(Base):
    """Bloque dentro de un template DMO."""
    __tablename__ = "dmo_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("dmo_templates.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    color = Column(String(20), nullable=False, default="#3b82f6")
    sort_order = Column(Integer, nullable=False, default=0)
    is_money_block = Column(Boolean, nullable=False, default=False)
    # metric_type: "checkbox" | "quantity"
    metric_type = Column(String(20), nullable=False, default=METRIC_TYPE_CHECKBOX)
    metric_label = Column(String(60), nullable=True)
    metric_goal = Column(Integer, nullable=False, default=0)

    template = relationship("DmoTemplate", back_populates="blocks", lazy="joined")


class DmoAssignment(Base):
    """Que template DMO sigue cada vendedor (1:1 por workspace)."""
    __tablename__ = "dmo_assignments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "vendor_id", name="uq_dmo_assignment_workspace_vendor"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("dmo_templates.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship("User", lazy="joined")
    template = relationship("DmoTemplate", lazy="joined")


class DmoLog(Base):
    """Reporte diario de un vendedor en un bloque (upsert por vendor+block+date).

    UNIQUE (vendor_id, block_id, date): protege contra logs duplicados. En
    AgentFlow esto se parcho a mano (script `fix_dmo_duplicates`); aca la
    proteccion viene de fabrica en el diseno del schema.
    """
    __tablename__ = "dmo_logs"
    __table_args__ = (
        UniqueConstraint("vendor_id", "block_id", "date", name="uq_dmo_log_vendor_block_date"),
        Index("ix_dmo_logs_vendor_date", "vendor_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    block_id = Column(Integer, ForeignKey("dmo_blocks.id"), nullable=False)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    metric_value = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship("User", lazy="joined")
    block = relationship("DmoBlock", lazy="joined")
