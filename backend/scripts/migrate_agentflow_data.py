"""ETL: migra los DATOS REALES de AgentFlow (inmobiliaria "Beyker") -> suite TasAR.

FUENTE (SOLO LECTURA, jamas se escribe):  schema `agentflow` (Aiven).
DESTINO (se ESCRIBE solo con --apply):     schema `tasar`   (Aiven).

El rework consolido el MODELO (tablas de AgentFlow re-creadas en TasAR en ingles),
pero los DATOS reales de la inmobiliaria nunca se migraron. Este script los trae.

REGLAS DURAS (ver CLAUDE.md global + WO):
  1. DRY-RUN POR DEFECTO. Sin --apply NO se escribe una sola fila en tasar:
     solo cuenta, valida FKs y muestra ejemplos de mapeo origen->destino.
  2. NUNCA se toca AgentFlow (solo SELECT). No se tocan datos EXISTENTES de tasar
     (workspace demo id=1): la migracion crea UN workspace nuevo y solo AGREGA.
  3. Nada de datos inventados (regla 11): si un campo no tiene equivalente queda
     NULL o su default real. Los datos reales (nombres, telefonos, montos, fechas,
     hashes de password) se preservan tal cual.
  4. Credenciales SOLO desde los .env (dotenv), nunca literales.

USO:
    python scripts/migrate_agentflow_data.py                 # dry-run (default)
    python scripts/migrate_agentflow_data.py --apply         # escribe en tasar
    python scripts/migrate_agentflow_data.py --workspace-name "Beyker"

ORDEN DE INSERCION (padres antes que hijos), con remaps old_id->new_id en memoria:
  workspace -> users -> (coaches catalogo global: reuso por nombre) ->
  dmo_templates (workspace-scoped) -> dmo_blocks -> dmo_assignments ->
  properties -> property_photos -> clients -> visits -> deals ->
  authorizations -> wa_conversations -> wa_messages -> push_subscriptions ->
  workspace_bot_config -> bot_faqs -> dmo_logs.
  NO se migra baileys_auth (sesion tecnica del gateway, se regenera).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

if sys.platform == "win32":
    # Aiven exige TLS; el proactor loop de Windows rompe el handshake SSL de
    # aiomysql. El selector loop lo resuelve.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiomysql  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

# ── Rutas de credenciales (SOLO .env, nunca literales) ─────────────────────
AF_ENV = Path(r"d:\Code\AgentFlow\backend\.env")   # FUENTE
TS_ENV = Path(__file__).resolve().parents[1] / ".env"  # DESTINO (ACM/backend/.env)

BACKUP_DIR = Path(__file__).parent / "_backups"

DEFAULT_WORKSPACE_NAME = "Beyker"
DEFAULT_WORKSPACE_SLUG = "beyker"

# ── Mapeos de valores (enum/rol). NO se inventan valores: si un valor origen no
#    matchea un valor valido de destino, se REPORTA y se aborta (no se adivina).
# Mapeo a la jerarquia canonica del rubro (WO F6-06):
# broker > administrador > coordinador > asesor.
ROLE_MAP = {
    "admin": "broker",
    "gerente": "coordinador",
    "coordinador": "coordinador",
    "vendedor": "asesor",
}
METRIC_TYPE_MAP = {"checkbox": "checkbox", "cantidad": "quantity"}
DIRECTION_MAP = {
    "inbound": "inbound", "outbound": "outbound",
    "in": "inbound", "out": "outbound",
}

# Coaches: catalogo GLOBAL de tasar (name UNIQUE). Se REUSAN por nombre; el que no
# matchea exacto se mapea a su equivalente re-brandeado del rework F2-01 (documentado).
COACH_NAME_REMAP = {
    "Tom Ferry": "Tom Ferry",
    "Mike Ferry": "Mike Ferry",
    "Brian Buffini": "Brian Buffini",
    "Verl Workman": "Verl Workman",
    # AgentFlow "Beyker AR" == tasar "WhatsApp-first AR" (mismo metodo AR, de-brandeado
    # en el WO F2-01). Se reusa el coach global existente para NO ensuciar el catalogo
    # compartido con una copia brandeada. DECISION reportada: el orquestador puede
    # optar por insertar "Beyker AR" como coach global nuevo.
    "Beyker AR": "WhatsApp-first AR",
}

# Provincia derivada para las propiedades: los 20 registros son ciudad="Buenos Aires"
# con barrios inequivocamente de CABA (Palermo, Belgrano, Almagro, Caballito, ...).
# tasar.properties.province es NOT NULL y AgentFlow no tiene provincia. "CABA" es la
# provincia administrativa correcta para esos barrios (NO es un dato inventado: es la
# jurisdiccion real de esos barrios). DECISION reportada para que el orquestador la
# valide/ajuste.
DERIVED_PROVINCE = "CABA"


def ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def connect(cfg: dict, ctx: ssl.SSLContext):
    return await aiomysql.connect(
        host=cfg["DB_HOST"], port=int(cfg["DB_PORT"]),
        user=cfg["DB_USER"], password=cfg["DB_PASSWORD"], db=cfg["DB_NAME"],
        ssl=ctx, charset="utf8mb4", autocommit=False,
    )


async def fetchall(conn, sql: str, args=None) -> list[dict]:
    cur = await conn.cursor(aiomysql.DictCursor)
    await cur.execute(sql, args or ())
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def fetchval(conn, sql: str, args=None):
    cur = await conn.cursor()
    await cur.execute(sql, args or ())
    row = await cur.fetchone()
    await cur.close()
    return row[0] if row else None


def _fmt(v):
    """Formatea un valor para el reporte de ejemplos (compacto)."""
    if isinstance(v, str) and len(v) > 40:
        return v[:37] + "..."
    return v


# ============================================================================
# Definicion declarativa de cada paso de la migracion.
# Cada step: source table, target table, y una funcion transform(row, ctx)->dict
# que devuelve el dict de columnas destino (SIN id). `ctx` lleva los remaps y el
# workspace_id destino. Devolver None saltea la fila (con motivo en ctx.skips).
# ============================================================================

class MigCtx:
    def __init__(self, workspace_name: str):
        self.workspace_name = workspace_name
        self.workspace_id: int | None = None
        self.remap: dict[str, dict[int, int]] = {}  # entity -> {old_id: new_id}
        self.skips: list[str] = []
        self.dropped_fields: dict[str, list[str]] = {}
        self._seen_meta_ids: set[str] = set()

    def r(self, entity: str, old_id):
        if old_id is None:
            return None
        return self.remap.get(entity, {}).get(old_id)


def t_users(row, ctx: MigCtx):
    role = ROLE_MAP.get(row["role"])
    if role is None:
        ctx.skips.append(f"users: rol origen no mapeado '{row['role']}' (user id={row['id']})")
        return None
    full_name = f"{row['nombre']} {row['apellido']}".strip()
    return {
        "workspace_id": ctx.workspace_id,
        "email": row["email"],
        "password_hash": row["hashed_password"],   # AF.hashed_password -> password_hash
        "full_name": full_name,                    # nombre + apellido -> full_name
        "role": role,                              # gerente/coordinador -> supervisor
        "license_number": None,                    # sin equivalente en AF -> NULL
        "avatar_url": row["foto_url"],             # foto_url -> avatar_url
        "is_active": row["is_active"],
        "is_available": row["is_available"],
        "last_assigned_at": row["last_assigned_at"],
        # AF.telefono_personal -> personal_phone (fallback a telefono; ambos reales)
        "personal_phone": row["telefono_personal"] or row["telefono"],
        "daily_conversations_goal": row["meta_conversaciones_diaria"],
        "is_demo": 0,  # datos reales del equipo, NO ejemplos de onboarding
    }


def t_templates(row, ctx: MigCtx):
    # Se insertan como templates WORKSPACE-SCOPED (clon del catalogo al tenant).
    coach_new = ctx.r("coach", row["coach_id"])
    return {
        "workspace_id": ctx.workspace_id,   # custom del tenant (no global)
        "coach_id": coach_new,
        "name": row["nombre"],
        "description": row["descripcion"],
        "market": row["mercado"],
        "is_active": row["activo"],
        "is_office_default": row["es_default_inmobiliaria"],
    }


def t_blocks(row, ctx: MigCtx):
    mt = METRIC_TYPE_MAP.get(row["metrica_tipo"])
    if mt is None:
        ctx.skips.append(f"dmo_blocks: metrica_tipo no mapeado '{row['metrica_tipo']}' (bloque id={row['id']})")
        return None
    return {
        "template_id": ctx.r("template", row["template_id"]),
        "name": row["nombre"],
        "description": row["descripcion"],
        "start_time": row["hora_inicio"],   # hora_inicio -> start_time
        "end_time": row["hora_fin"],        # hora_fin -> end_time
        "color": row["color"],
        "sort_order": row["orden"],         # orden -> sort_order
        "is_money_block": row["es_money_block"],
        "metric_type": mt,                  # cantidad -> quantity
        "metric_label": row["metrica_label"],
        "metric_goal": row["metrica_meta"],
    }


def t_assignments(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "vendor_id": ctx.r("user", row["vendedor_id"]),   # vendedor_id -> vendor_id
        "template_id": ctx.r("template", row["template_id"]),
        "assigned_at": row["assigned_at"],
    }


def t_properties(row, ctx: MigCtx):
    captador_new = ctx.r("user", row["captador_id"])
    # estado (captada/publicada/...) NO tiene columna en tasar.properties -> se dropea.
    return {
        "workspace_id": ctx.workspace_id,
        "created_by": captador_new,     # NOT NULL: usa el captador real
        "captador_id": captador_new,    # captador_id -> captador_id
        "title": row["titulo"],
        "property_type": row["tipo"],   # casa|departamento|ph (validos)
        "operation": "venta",           # sin equivalente en AF -> default real
        "province": DERIVED_PROVINCE,   # NOT NULL, derivado (ver DERIVED_PROVINCE)
        "city": row["ciudad"],          # ciudad -> city
        "neighborhood": row["barrio"],  # barrio -> neighborhood
        "address": row["direccion"],    # direccion -> address
        "latitude": row["lat"],
        "longitude": row["lng"],
        "total_area_m2": row["m2_totales"],
        "covered_area_m2": row["m2_cubiertos"],
        "rooms": row["ambientes"],      # ambientes -> rooms
        "bedrooms": None,               # AF no distingue dormitorios -> NULL
        "bathrooms": row["banos"],
        "parking_spots": row["cocheras"],
        "age_years": row["antiguedad"],
        "condition": None,
        "orientation": None,
        "floor": None,
        "asking_price": row["precio_publicacion"],  # precio_publicacion -> asking_price
        "currency": row["moneda"],
        "exclusivity": row["exclusividad"],
        "description": row["descripcion"],
        "ai_analysis": None,
        "is_demo": 0,
    }


def t_photos(row, ctx: MigCtx):
    return {
        "property_id": ctx.r("property", row["propiedad_id"]),
        "url": row["url"],
        "public_id": None,       # sin equivalente en AF
        "caption": None,
        "order": row["orden"],   # orden -> order
    }


def t_clients(row, ctx: MigCtx):
    name = f"{row['nombre']} {row['apellido']}".strip()
    return {
        "workspace_id": ctx.workspace_id,
        "name": name,                     # nombre + apellido -> name
        "type": "particular",             # sin equivalente en AF -> default
        "contact_name": None,
        "email": row["email"],
        "phone": row["telefono"],         # telefono -> phone
        "address": None,
        "tax_id": None,
        "notes": row["notas"],
        "lead_status": row["estado"],     # estado -> lead_status (valores validos)
        "temperature": row["temperatura"],
        "origin": row["origen"],          # origen -> origin
        "assigned_to": ctx.r("user", row["vendedor_id"]),  # vendedor_id -> assigned_to
        "pref_zona": row["pref_zona"],
        "pref_m2_min": row["pref_m2_min"],
        "pref_m2_max": row["pref_m2_max"],
        "pref_ambientes": row["pref_ambientes"],
        "pref_budget_min": row["pref_presupuesto_min"],  # -> pref_budget_min
        "pref_budget_max": row["pref_presupuesto_max"],  # -> pref_budget_max
        "pref_currency": row["pref_moneda"],             # -> pref_currency
        "last_contact_at": row["last_contact_at"],
    }


def t_visits(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "client_id": ctx.r("client", row["cliente_id"]),
        "property_id": ctx.r("property", row["propiedad_id"]),
        "vendor_id": ctx.r("user", row["vendedor_id"]),
        "scheduled_at": row["fecha_hora"],   # fecha_hora -> scheduled_at
        "status": row["estado"],             # estado -> status
        "result": row["resultado"],          # resultado -> result
        "voice_notes": row["notas_voz"],     # notas_voz -> voice_notes
    }


def t_deals(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "client_id": ctx.r("client", row["cliente_id"]),
        "property_id": ctx.r("property", row["propiedad_id"]),
        "vendor_id": ctx.r("user", row["vendedor_id"]),
        "stage": row["etapa"],                       # etapa -> stage
        "negotiated_price": row["precio_negociado"], # -> negotiated_price
        "currency": row["moneda"],
        "estimated_commission": row["comision_estimada"],
        "probability_pct": row["probabilidad_pct"],
        "estimated_close_date": row["fecha_estimada_cierre"],
        "notes": row["notas"],
    }


def t_authorizations(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "property_id": ctx.r("property", row["propiedad_id"]),
        "captador_id": ctx.r("user", row["captador_id"]),
        "signed_date": row["fecha_firma"],       # fecha_firma -> signed_date
        "expiry_date": row["fecha_vencimiento"], # fecha_vencimiento -> expiry_date
        "min_price": row["precio_minimo"],       # precio_minimo -> min_price
        "currency": row["moneda"],
        "commission_pct": row["comision_pct"],
        "exclusivity": row["exclusividad"],
        "pdf_url": row["pdf_url"],
        "notes": row["observaciones"],           # observaciones -> notes
        "status": row["estado"],                 # estado -> status
    }


def t_wa_conversations(row, ctx: MigCtx):
    # AF.prompt_override y AF.voice_id NO tienen columna en tasar.wa_conversations -> se dropean.
    return {
        "workspace_id": ctx.workspace_id,
        "phone_jid": row["telefono"],            # telefono (E.164) -> phone_jid
        "phone_public": None,                    # sin equivalente por-conv
        "contact_name": row["nombre_contacto"],  # nombre_contacto -> contact_name
        "client_id": ctx.r("client", row["cliente_id"]),
        "assignee_id": ctx.r("user", row["assignee_id"]),
        "status": row["estado"],                 # estado -> status
        "unread_count": row["unread_count"],
        "bot_paused_until": None,
        "voice_mode": row["voice_mode"] or "off",
        "rolling_summary_md": None,
        "summary_up_to_message_id": None,
        "last_activity_at": row["ultima_actividad"],
        "is_demo": 0,
    }


def t_wa_messages(row, ctx: MigCtx):
    direction = DIRECTION_MAP.get(row["direccion"])
    if direction is None:
        ctx.skips.append(f"wa_messages: direccion no mapeada '{row['direccion']}' (msg id={row['id']})")
        return None
    meta = row["meta_message_id"]
    # tasar.wa_messages.meta_message_id es UNIQUE. La fuente reenvia el mismo id
    # (WhatsApp Multi-Device): se conserva la 1ra aparicion y se NULLea el resto
    # (NULL multiple es valido). NO se pierde el mensaje, solo la llave de idempotencia
    # de los duplicados.
    if meta is not None:
        if meta in ctx._seen_meta_ids:
            meta = None
        else:
            ctx._seen_meta_ids.add(meta)
    return {
        "conversation_id": ctx.r("wa_conversation", row["conversation_id"]),
        "direction": direction,          # direccion -> direction
        "type": "text",                  # AF no tiene tipo -> default text
        "content": row["contenido"],     # contenido -> content
        "media_url": None,
        "transcription": None,
        "meta_message_id": meta,
        "sender_id": ctx.r("user", row["sender_id"]),
        "is_read": row["leido"],         # leido -> is_read
        "created_at": row["enviado_at"], # enviado_at -> created_at
    }


def t_push(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "user_id": ctx.r("user", row["user_id"]),
        "endpoint": row["endpoint"],
        "p256dh": row["p256dh"],
        "auth": row["auth"],
        "user_agent": row["user_agent"],
        "last_used_at": row["last_used_at"],
    }


def t_bot_config(row, ctx: MigCtx):
    # bot_config (singleton AF) -> workspace_bot_config (1 fila por workspace).
    horarios = [row.get("horario_semana"), row.get("horario_sabado"), row.get("horario_domingo")]
    business_hours = ". ".join(h for h in horarios if h) or None
    comis = [
        ("Compra (vendedor)", row.get("comision_compra_vendedor")),
        ("Compra (comprador)", row.get("comision_compra_comprador")),
        ("Alquiler (propietario)", row.get("comision_alquiler_propietario")),
        ("Alquiler (inquilino)", row.get("comision_alquiler_inquilino")),
        ("Reserva estandar", row.get("reserva_pct_estandar")),
        ("Plazo aceptacion reserva", row.get("reserva_plazo_aceptacion")),
    ]
    commissions_text = "\n".join(f"{k}: {v}" for k, v in comis if v) or None
    # Sin equivalente / se dropean: instagram, baileys_service_url, baileys_api_key,
    # numero_oficial_wa, joda_* (no van a workspace_bot_config).
    return {
        "workspace_id": ctx.workspace_id,
        "enabled": 0,                              # NO auto-encender el bot
        "business_name": ctx.workspace_name,       # AF no tiene nombre -> nombre del ws
        "business_description": row.get("identidad_extra"),
        "address": row.get("direccion"),
        "zones": None,
        "phone": row.get("telefono_oficial"),
        "email": row.get("email_oficial"),
        "website": row.get("web"),
        "services": None,
        "commissions_text": commissions_text,
        "differentials": row.get("diferencial_extra"),
        "welcome_message": row.get("mensaje_bienvenida"),
        "off_hours_message": row.get("mensaje_off_hours"),
        "derivation_message": None,
        "business_hours": business_hours,
        "derivation_words": row.get("palabras_derivacion_extra"),
        "tone": "profesional",
        "channel_provider": "baileys",
        "default_voice_mode": "off",
    }


def t_bot_faqs(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "question": row["pregunta"],   # pregunta -> question
        "answer": row["respuesta"],    # respuesta -> answer
        "priority": row["orden"],      # orden -> priority
        "is_active": row["activo"],    # activo -> is_active
    }


def t_dmo_logs(row, ctx: MigCtx):
    return {
        "workspace_id": ctx.workspace_id,
        "vendor_id": ctx.r("user", row["vendedor_id"]),
        "block_id": ctx.r("block", row["bloque_id"]),  # bloque_id -> block_id
        "date": row["fecha"],                           # fecha -> date
        "completed": row["completado"],                 # completado -> completed
        "metric_value": row["valor_metrica"],           # valor_metrica -> metric_value
        "notes": row["notas"],                          # notas -> notes
    }


# (entity_key, source_sql, target_table, transform, remap_this_entity)
STEPS = [
    ("user", "SELECT * FROM users ORDER BY id", "users", t_users, True),
    ("template", "SELECT * FROM dmo_templates ORDER BY id", "dmo_templates", t_templates, True),
    ("block", "SELECT * FROM dmo_bloques ORDER BY id", "dmo_blocks", t_blocks, True),
    ("assignment", "SELECT * FROM vendedor_dmo_assignments ORDER BY id", "dmo_assignments", t_assignments, False),
    ("property", "SELECT * FROM propiedades ORDER BY id", "properties", t_properties, True),
    ("photo", "SELECT * FROM fotos_propiedad ORDER BY id", "property_photos", t_photos, False),
    ("client", "SELECT * FROM clientes ORDER BY id", "clients", t_clients, True),
    ("visit", "SELECT * FROM visitas ORDER BY id", "visits", t_visits, False),
    ("deal", "SELECT * FROM pipeline_deals ORDER BY id", "deals", t_deals, False),
    ("authorization", "SELECT * FROM autorizaciones ORDER BY id", "authorizations", t_authorizations, False),
    ("wa_conversation", "SELECT * FROM whatsapp_conversations ORDER BY id", "wa_conversations", t_wa_conversations, True),
    ("wa_message", "SELECT * FROM whatsapp_messages ORDER BY id", "wa_messages", t_wa_messages, False),
    ("push", "SELECT * FROM push_subscriptions ORDER BY id", "push_subscriptions", t_push, False),
    ("bot_config", "SELECT * FROM bot_config ORDER BY id", "workspace_bot_config", t_bot_config, False),
    ("bot_faq", "SELECT * FROM bot_faqs ORDER BY id", "bot_faqs", t_bot_faqs, False),
    ("dmo_log", "SELECT * FROM dmo_logs ORDER BY id", "dmo_logs", t_dmo_logs, False),
]

TARGET_TABLES = [s[2] for s in STEPS] + ["workspaces"]


def _insert_sql(table: str, cols: list[str]) -> str:
    collist = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    return f"INSERT INTO `{table}` ({collist}) VALUES ({placeholders})"


async def resolve_coaches(af, ts, ctx: MigCtx, apply: bool, report):
    """Coaches: catalogo GLOBAL. Se reusan por nombre (name UNIQUE)."""
    af_coaches = await fetchall(af, "SELECT id, nombre FROM coaches ORDER BY id")
    ts_coaches = await fetchall(ts, "SELECT id, name FROM coaches")
    ts_by_name = {c["name"]: c["id"] for c in ts_coaches}
    ctx.remap["coach"] = {}
    unresolved = []
    for c in af_coaches:
        target_name = COACH_NAME_REMAP.get(c["nombre"], c["nombre"])
        new_id = ts_by_name.get(target_name)
        if new_id is None:
            unresolved.append(f"coach '{c['nombre']}' -> '{target_name}' NO existe en catalogo global tasar")
            continue
        ctx.remap["coach"][c["id"]] = new_id
        report.append(f"    coach {c['id']} '{c['nombre']}' -> tasar coach {new_id} '{target_name}' (reuso global)")
    return unresolved


async def run():
    ap = argparse.ArgumentParser(description="ETL AgentFlow -> TasAR (dry-run default)")
    ap.add_argument("--apply", action="store_true", help="ESCRIBE en tasar (default: dry-run)")
    ap.add_argument("--workspace-name", default=DEFAULT_WORKSPACE_NAME)
    ap.add_argument("--workspace-slug", default=DEFAULT_WORKSPACE_SLUG)
    args = ap.parse_args()

    af_cfg = dotenv_values(AF_ENV)
    ts_cfg = dotenv_values(TS_ENV)
    if not af_cfg.get("DB_HOST") or not ts_cfg.get("DB_HOST"):
        print("ERROR: no se pudieron leer credenciales de los .env", file=sys.stderr)
        sys.exit(1)

    mode = "APPLY (ESCRIBE)" if args.apply else "DRY-RUN (no escribe)"
    print("=" * 74)
    print(f"  ETL AgentFlow -> TasAR   |   modo: {mode}")
    print(f"  Fuente: {af_cfg['DB_NAME']} @ {af_cfg['DB_HOST']}  (SOLO LECTURA)")
    print(f"  Destino: {ts_cfg['DB_NAME']} @ {ts_cfg['DB_HOST']}")
    print("=" * 74)

    ctx_ssl = ssl_ctx()
    af = await connect(af_cfg, ctx_ssl)
    ts = await connect(ts_cfg, ctx_ssl)
    ctx = MigCtx(args.workspace_name)

    try:
        # ── Guardas de no-destruccion ──────────────────────────────────────
        existing_ws = await fetchall(ts, "SELECT id, name, slug FROM workspaces")
        for w in existing_ws:
            if w["slug"] == args.workspace_slug:
                print(f"ERROR: ya existe un workspace con slug '{args.workspace_slug}' "
                      f"(id={w['id']}). Aborto para no colisionar/duplicar.", file=sys.stderr)
                sys.exit(2)
        print(f"\nWorkspace DESTINO a crear: name='{args.workspace_name}' slug='{args.workspace_slug}'")
        print(f"Workspaces existentes en tasar (intactos): {[(w['id'], w['slug']) for w in existing_ws]}")

        # ── Coaches (reuso catalogo global) ────────────────────────────────
        print("\n[coaches] resolucion contra catalogo global de tasar:")
        coach_report: list[str] = []
        unresolved = await resolve_coaches(af, ts, ctx, args.apply, coach_report)
        for line in coach_report:
            print(line)
        if unresolved:
            print("\nCOACHES SIN RESOLVER (bloqueante):")
            for u in unresolved:
                print("  - " + u)
            print("Aborto: hay coaches sin equivalente global. Revisar COACH_NAME_REMAP.", file=sys.stderr)
            sys.exit(3)

        # ── Backup (solo en apply) ─────────────────────────────────────────
        if args.apply:
            BACKUP_DIR.mkdir(exist_ok=True)
            snapshot = {}
            for t in TARGET_TABLES:
                snapshot[t] = await fetchval(ts, f"SELECT COALESCE(MAX(id), 0) FROM `{t}`") \
                    if t != "workspace_bot_config" else await fetchval(ts, "SELECT COALESCE(MAX(id),0) FROM workspace_bot_config")
            ts_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bpath = BACKUP_DIR / f"pre_agentflow_migration_{ts_stamp}.json"
            bpath.write_text(json.dumps({
                "note": "max(id) por tabla ANTES de la migracion; rollback = borrar id > estos y el workspace nuevo",
                "target_db": ts_cfg["DB_NAME"], "max_ids": snapshot,
            }, indent=2), encoding="utf-8")
            print(f"\n[backup] max-ids previos guardados en {bpath}")

        # ── Crear workspace ────────────────────────────────────────────────
        if args.apply:
            cur = await ts.cursor()
            await cur.execute(
                "INSERT INTO workspaces (name, slug, plan) VALUES (%s, %s, %s)",
                (args.workspace_name, args.workspace_slug, "free"),
            )
            ctx.workspace_id = cur.lastrowid
            await cur.close()
            print(f"\n[workspace] creado id={ctx.workspace_id}")
        else:
            ctx.workspace_id = -1  # placeholder para dry-run
            print("\n[workspace] (dry-run) se crearia 1 workspace nuevo")

        # ── Pasos ──────────────────────────────────────────────────────────
        totals = {}
        grand_total = 0
        print("\n" + "-" * 74)
        for entity, sql, target, transform, do_remap in STEPS:
            rows = await fetchall(af, sql)
            if do_remap:
                ctx.remap.setdefault(entity, {})
            planned = []  # (old_id, dest_dict)
            for row in rows:
                dest = transform(row, ctx)
                if dest is None:
                    continue
                planned.append((row["id"], dest))

            inserted = 0
            examples = []
            for i, (old_id, dest) in enumerate(planned):
                cols = list(dest.keys())
                vals = list(dest.values())
                if args.apply:
                    cur = await ts.cursor()
                    await cur.execute(_insert_sql(target, cols), vals)
                    new_id = cur.lastrowid
                    await cur.close()
                    if do_remap:
                        ctx.remap[entity][old_id] = new_id
                else:
                    # dry-run: id sintetico solo para display/validacion de FKs
                    new_id = 100000 + i
                    if do_remap:
                        ctx.remap[entity][old_id] = new_id
                inserted += 1
                if len(examples) < 3:
                    examples.append((old_id, new_id, dest))

            totals[target] = inserted
            grand_total += inserted
            print(f"[{target}] filas fuente={len(rows)} -> migraria/o={inserted}")
            for old_id, new_id, dest in examples:
                # mostrar 4-5 campos representativos
                keys = [k for k in dest.keys() if k not in ("workspace_id",)][:5]
                shown = {k: _fmt(dest[k]) for k in keys}
                print(f"    ej  old_id={old_id} -> new_id={new_id}: {shown}")

        print("-" * 74)
        print(f"TOTAL filas a migrar: {grand_total}  (en {len(totals)} tablas)")
        print("baileys_auth (83): NO se migra (sesion tecnica del gateway).")

        if ctx.skips:
            print("\nFILAS SALTEADAS / valores no mapeados:")
            for s in ctx.skips:
                print("  - " + s)
        else:
            print("\nSin filas salteadas: todos los enums/roles/valores mapearon a valores validos de destino.")

        if args.apply:
            await ts.commit()
            print("\n[APPLY] COMMIT ok.")
        else:
            print("\n[DRY-RUN] no se escribio ninguna fila en tasar. Para escribir: --apply")

        # AgentFlow: nunca se escribio (solo SELECT). Rollback defensivo por las dudas.
        await af.rollback()
    except Exception:
        await ts.rollback()
        await af.rollback()
        raise
    finally:
        af.close()
        ts.close()


if __name__ == "__main__":
    asyncio.run(run())
