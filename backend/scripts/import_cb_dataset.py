"""ETL: dataset Coldwell Banker Argentina -> market_listings (WO F0-06).

Fuente (repo donante, SOLO LECTURA): d:\\Code\\beykercoldwell\\src\\data\\
  - cb-argentina.json          (listado: 9240 propiedades, campos "RawProperty")
  - cb-argentina-details.json  (detalle por id: antiguedad, lat/lng, address, city, province)

Patron OBLIGATORIO (regla dura del WO): --dry-run (default) -> parsea, joinea,
mapea, aplica sanidad y dedup, imprime reporte. SIN escribir a ninguna DB.
--apply (no ejecutado por el implementador; lo corre el dueno/Infra) hace backup
JSON de market_listings y recien ahi inserta.

Todos los imports de `core.*` / `models.*` (que requieren settings de DB) son
LAZY -- se importan solo dentro de las funciones de --apply. Esto garantiza que
--dry-run corra standalone, sin .env, sin conexion, sin tocar la Aiven.

Cumple regla #11 (CLAUDE.md global): nunca se inventan datos. Precios en ARS
sin cotizacion confiable se EXCLUYEN (no se convierten con un tipo de cambio
supuesto). Filas sin precio/superficie se excluyen. Coordenadas fuera de la
bounding box de Argentina se descartan (quedan NULL) en vez de graficarse mal.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ============================================================================
# Constantes / defaults
# ============================================================================

REPO_DONANTE = Path(r"d:\Code\beykercoldwell\src\data")
DEFAULT_PROPERTIES_JSON = REPO_DONANTE / "cb-argentina.json"
DEFAULT_DETAILS_JSON = REPO_DONANTE / "cb-argentina-details.json"

SOURCE_TAG = "cb-argentina-2026-05"

MIN_USD_M2 = 200
MAX_USD_M2 = 15000

# Bounding box generosa de Argentina continental + insular (para descartar
# geocodes rotos del scrape, ej. lat=40 que cae en el hemisferio norte).
AR_LAT_RANGE = (-56.0, -21.0)
AR_LNG_RANGE = (-74.0, -53.0)

BACKUP_DIR = Path(__file__).parent / "_backups"

# property_type soportados por el frontend (Propiedades.tsx TYPE_OPTIONS):
# casa | departamento | ph | terreno | local | oficina
PROPERTY_TYPE_MAP = {
    "departamento": "departamento",
    "casa": "casa",
    "ph": "ph",
    "terreno o lote": "terreno",
    "terreno comercial": "terreno",
    "terreno industrial": "terreno",
    "local comercial": "local",
    "oficina": "oficina",
}

SUPPORTED_OPERATIONS = {"venta", "alquiler"}

# CABA en el dataset CB viene como province="Capital Federal" y el barrio
# (Palermo, Recoleta, ...) en el campo "city" del detalle. La convención del
# resto de la app (seed_v2.py) es province="CABA", city="CABA",
# neighborhood=<barrio>. Normalizamos SOLO para CABA (mapeo 1:1 determinístico,
# no inventa nada). Para GBA/interior dejamos province/city tal cual vienen.
CABA_PROVINCE_ALIASES = {"capital federal", "caba", "ciudad autonoma de buenos aires"}

ORIENTATION_MAP = {
    "norte": "norte", "sur": "sur", "este": "este", "oeste": "oeste",
    "noreste": "noreste", "noroeste": "noroeste",
    "sureste": "sureste", "suroeste": "suroeste",
}

# ============================================================================
# Deteccion de features (puerto de src/lib/feature-index.ts::detectFeatures)
# ============================================================================

FEATURE_DICT: list[tuple[str, list[str]]] = [
    ("pileta", ["pileta", "piscina"]),
    ("cochera", ["cochera", "garage", "garaje"]),
    ("parrilla", ["parrilla", "asador"]),
    ("balcon", ["balcon"]),
    ("terraza", ["terraza"]),
    ("patio", ["patio"]),
    ("quincho", ["quincho"]),
    ("amenities", ["amenities", "amenity"]),
    ("gym", ["gym", "gimnasio"]),
    ("sum", ["sum ", " sum.", "salon de usos"]),
    ("lavadero", ["lavadero", "laundry"]),
    ("vestidor", ["vestidor", "walk in"]),
    ("baulera", ["baulera"]),
    ("ascensor", ["ascensor"]),
    ("jardin", ["jardin", "parque privado", "parque propio"]),
    ("apto_credito", ["apto credito", "apto credit", "apto cr ", "apto cr.", "apto-credito"]),
    ("apto_profesional", ["apto profesional", "apto consultor", "consultorio"]),
    ("seguridad_24h", ["seguridad 24", "vigilancia 24", "seguridad las 24"]),
    ("vista_despejada", ["vista despejada", "vista panor", "vista al rio", "vista abierta"]),
    ("luminoso", ["luminoso", "luminosa", "muy luminos", "gran luminosidad"]),
    ("a_estrenar", ["a estrenar", "estrena", "estrenar"]),
    ("en_pozo", ["en pozo", "pre venta", "preventa", "en construccion"]),
    ("reciclado", ["reciclad", "a reciclar", "reciclar"]),
    ("dependencia", ["dependencia", "cuarto de servicio"]),
]


def _strip_accents(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def normalize_text(s: str | None) -> str:
    return _strip_accents((s or "").lower())


def detect_features(text: str) -> list[str]:
    norm = normalize_text(text)
    out = []
    for key, patterns in FEATURE_DICT:
        if any(p in norm for p in patterns):
            out.append(key)
    return out


# ============================================================================
# Carga de los 2 JSON (SOLO json.load + iteracion -- nunca Read tool en 6.7MB)
# ============================================================================

def load_properties(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("properties", [])


def load_details(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("details", {})


# ============================================================================
# Mapeo campo a campo
# ============================================================================

def map_property_type(raw_type: str | None) -> str | None:
    return PROPERTY_TYPE_MAP.get(normalize_text(raw_type))


def map_location(detail: dict) -> tuple[str | None, str | None, str | None]:
    """(province, city, neighborhood) a partir del detalle CB.

    CABA: province -> "CABA", city -> "CABA", neighborhood -> barrio (detail.city).
    Resto: province/city tal cual vienen del detalle (sin normalizar), sin
    barrio (CB no da ese nivel de detalle para GBA/interior).
    """
    raw_province = (detail.get("province") or "").strip()
    raw_city = (detail.get("city") or "").strip()
    if normalize_text(raw_province) in CABA_PROVINCE_ALIASES:
        return "CABA", "CABA", (raw_city or None)
    return (raw_province or None), (raw_city or None), None


def map_orientation(raw: str | None) -> str | None:
    return ORIENTATION_MAP.get(normalize_text(raw))


def map_coords(detail: dict) -> tuple[float | None, float | None]:
    lat, lng = detail.get("lat"), detail.get("lng")
    if lat is None or lng is None:
        return None, None
    lat_ok = AR_LAT_RANGE[0] <= lat <= AR_LAT_RANGE[1]
    lng_ok = AR_LNG_RANGE[0] <= lng <= AR_LNG_RANGE[1]
    if lat_ok and lng_ok:
        return float(lat), float(lng)
    return None, None  # geocode roto del scrape -- no se inventa, se descarta


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[.,#\-]")


def normalize_address_key(address: str | None, total_area_m2: float, price: float) -> str:
    addr_norm = _WS_RE.sub(" ", _PUNCT_RE.sub(" ", normalize_text(address))).strip()
    return f"{addr_norm}|{round(total_area_m2, 1)}|{round(price, 2)}"


# ============================================================================
# Mapeo de una fila + sanidad (devuelve (row_dict, None) o (None, causa))
# ============================================================================

def map_row(prop: dict, detail: dict | None) -> tuple[dict | None, str | None]:
    if detail is None:
        return None, "sin_detalle_join"

    price = prop.get("priceValue")
    if price is None:
        return None, "sin_precio"

    title = (prop.get("title") or "").strip()
    if not title:
        return None, "sin_titulo"

    currency = (prop.get("priceCurrency") or "").strip().upper()
    if currency == "ARS":
        return None, "ars_sin_cotizacion_confiable"
    if currency != "USD":
        return None, "moneda_no_soportada"

    surface = prop.get("surfaceM2")
    if surface is None or surface <= 0:
        return None, "sin_superficie"

    ptype = map_property_type(prop.get("type"))
    if ptype is None:
        return None, "tipo_no_soportado"

    operation = (prop.get("operacion") or "").strip().lower()
    if operation not in SUPPORTED_OPERATIONS:
        return None, "operacion_no_soportada"

    usd_m2 = round(price / surface, 2)
    if not (MIN_USD_M2 <= usd_m2 <= MAX_USD_M2):
        return None, "usd_m2_fuera_de_rango"

    province, city, neighborhood = map_location(detail)
    lat, lng = map_coords(detail)
    address = (detail.get("address") or "").strip() or None
    description = (prop.get("description") or "").replace("�", " ").strip() or None
    title_clean = title.replace("�", " ").strip()
    features = detect_features(f"{title_clean} {description or ''}")
    external_id = (prop.get("reference") or "").strip() or prop["id"]

    row = dict(
        source=SOURCE_TAG,
        source_url=prop.get("detailUrl") or None,
        external_id=external_id,
        title=title_clean[:200],
        property_type=ptype,
        operation=operation,
        province=province,
        city=city,
        neighborhood=neighborhood,
        address=address,
        latitude=lat,
        longitude=lng,
        total_area_m2=float(surface),
        covered_area_m2=None,  # CB no distingue cubierta/total -- no se inventa
        rooms=None,            # CB no trae "ambientes" estructurado -- no se infiere
        bedrooms=prop.get("bedrooms"),
        bathrooms=prop.get("bathrooms"),
        age_years=detail.get("antiguedadYears"),
        condition=None,        # CB no trae estado de conservacion estructurado
        orientation=map_orientation(detail.get("orientation")),
        floor=None,            # detail.floors es ambiguo (piso vs. altura del edificio)
        parking_spots=None,
        price=float(price),
        currency="USD",
        price_per_m2=usd_m2,
        status="active",
        days_on_market=None,
        description=description,
        photos_count=1 if prop.get("image") else 0,
        raw_data=json.dumps(
            {
                "features": features,
                "external_id": external_id,
                "source_url": prop.get("detailUrl"),
                "cb_id": prop.get("id"),
                "cb_type_raw": prop.get("type"),
                "cb_location_raw": prop.get("location"),
                "cb_antiquity_label": detail.get("antiquity"),
                "cb_situation": detail.get("situation"),
                "cb_floors_raw": detail.get("floors"),
                "cb_area_raw": detail.get("area"),
                "cb_image": prop.get("image"),
            },
            ensure_ascii=False,
        ),
    )
    return row, None


# ============================================================================
# ETL puro (sin DB) -- comparte codigo entre --dry-run y --apply
# ============================================================================

class EtlResult:
    def __init__(self) -> None:
        self.total_raw = 0
        self.rows: list[dict] = []
        self.exclusion_reasons: Counter = Counter()
        self.dup_dropped = 0
        self.dup_examples: list[tuple[str, dict, dict]] = []  # (key, kept, dropped)


def run_etl(properties_path: Path, details_path: Path) -> EtlResult:
    result = EtlResult()
    properties = load_properties(properties_path)
    details = load_details(details_path)
    result.total_raw = len(properties)

    mapped: list[dict] = []
    for prop in properties:
        detail = details.get(prop.get("id"))
        row, reason = map_row(prop, detail)
        if row is None:
            result.exclusion_reasons[reason] += 1
            continue
        mapped.append(row)

    # Dedup dentro del propio import: (direccion normalizada + m2 + precio).
    # Se queda con la primera aparicion; el resto se cuenta y se descarta.
    seen: dict[str, dict] = {}
    deduped: list[dict] = []
    for row in mapped:
        key = normalize_address_key(row["address"], row["total_area_m2"], row["price"])
        if key in seen:
            result.dup_dropped += 1
            if len(result.dup_examples) < 5:
                result.dup_examples.append((key, seen[key], row))
            continue
        seen[key] = row
        deduped.append(row)

    result.rows = deduped
    return result


# ============================================================================
# Reporte de --dry-run
# ============================================================================

def _fmt_row_brief(row: dict) -> str:
    return (
        f"[{row['property_type']:12s}] {row['city'] or '?':20s} "
        f"USD {row['price']:>10,.0f}  {row['total_area_m2']:>6.1f} m2  "
        f"({row['price_per_m2']:>7.1f} USD/m2)  ext_id={row['external_id']}"
    )


def print_dry_run_report(result: EtlResult, sample_n: int, spot_check_n: int) -> None:
    total_raw = result.total_raw
    total_excluded = sum(result.exclusion_reasons.values())
    total_mapped = total_raw - total_excluded
    total_importable = len(result.rows)

    print("=" * 78)
    print("DRY-RUN -- import_cb_dataset.py (WO F0-06)")
    print("=" * 78)
    print(f"Total filas en cb-argentina.json:        {total_raw}")
    print(f"Excluidas por sanidad (antes de dedup):   {total_excluded}")
    print(f"  Pasan sanidad (candidatas post-sanity):  {total_mapped}")
    print(f"Duplicadas dentro del import (descartadas): {result.dup_dropped}")
    print(f"IMPORTABLES (final, listas para --apply): {total_importable}")
    print()

    print("-- Exclusiones por causa --")
    for reason, count in result.exclusion_reasons.most_common():
        pct = 100 * count / total_raw if total_raw else 0
        print(f"  {reason:32s} {count:6d}  ({pct:5.1f}% del total)")
    print()

    print("-- Distribucion IMPORTABLES por tipo --")
    type_c = Counter(r["property_type"] for r in result.rows)
    for t, c in type_c.most_common():
        print(f"  {t:15s} {c:6d}")
    print()

    print("-- Distribucion IMPORTABLES por provincia (top 20) --")
    prov_c = Counter(r["province"] or "(sin provincia)" for r in result.rows)
    for p, c in prov_c.most_common(20):
        print(f"  {p:25s} {c:6d}")
    print()

    print("-- Distribucion IMPORTABLES por operacion --")
    op_c = Counter(r["operation"] for r in result.rows)
    for o, c in op_c.most_common():
        print(f"  {o:15s} {c:6d}")
    print()

    ars_excluded = result.exclusion_reasons.get("ars_sin_cotizacion_confiable", 0)
    print(f"ARS excluidas por falta de cotizacion confiable: {ars_excluded}")
    print()

    print(f"-- Muestra de {min(sample_n, total_importable)} filas (diff resumido) --")
    for row in result.rows[:sample_n]:
        print("  " + _fmt_row_brief(row))
    print()

    if result.dup_examples:
        print(f"-- Ejemplos de duplicados descartados (dedup direccion+m2+precio), max 5 --")
        for key, kept, dropped in result.dup_examples:
            print(f"  key={key}")
            print(f"    KEPT    ext_id={kept['external_id']}  title={kept['title'][:60]}")
            print(f"    DROPPED ext_id={dropped['external_id']}  title={dropped['title'][:60]}")
        print()

    print(f"-- Spot-check: {min(spot_check_n, total_importable)} filas completas mapeadas --")
    for row in result.rows[:spot_check_n]:
        print(json.dumps(row, ensure_ascii=False, indent=2, default=str))
        print()

    print("-- Dedup contra lo EXISTENTE en market_listings --")
    print("  N/A en --dry-run: no se conecta a ninguna DB (regla dura del WO).")
    print("  En --apply se recalcula esta misma dedup key contra las filas")
    print("  existentes (seed + imports previos) antes de insertar.")
    print()
    print("-- Filas source=NULL en market_listings (deberian ser 'seed') --")
    print("  N/A en --dry-run. En --apply se verifica y se documenta/backfillea.")
    print("=" * 78)


# ============================================================================
# --apply (implementado, NO ejecutado por el implementador de este WO)
# ============================================================================

async def _backup_existing(session) -> Path:
    """Vuelca TODA la tabla market_listings a un JSON con timestamp, antes de
    tocarla. Se corre siempre antes de cualquier insert/update en --apply."""
    from sqlalchemy import select
    from models.market_listing import MarketListing

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rows = (await session.execute(select(MarketListing))).scalars().all()
    payload = []
    for r in rows:
        payload.append({
            c.name: getattr(r, c.name).isoformat() if hasattr(getattr(r, c.name), "isoformat")
            else getattr(r, c.name)
            for c in MarketListing.__table__.columns
        })
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"market_listings_backup_{ts}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[apply] Backup de {len(payload)} filas -> {backup_path}")
    return backup_path


async def apply_import(properties_path: Path, details_path: Path) -> None:
    """Import real. Requiere backend/.env con credenciales validas de la Aiven
    compartida. NO se corre desde este WO -- lo dispara el dueno/Infra."""
    from sqlalchemy import select, update
    from core.database import AsyncSessionLocal
    from models.market_listing import MarketListing

    result = run_etl(properties_path, details_path)
    print(f"[apply] ETL en memoria: {len(result.rows)} filas importables "
          f"(de {result.total_raw} en el JSON origen).")

    async with AsyncSessionLocal() as session:
        await _backup_existing(session)

        # Backfill de source=NULL -> 'seed' en filas preexistentes (el default
        # Python "seed" del modelo no se aplica si la fila se inserto sin pasar
        # por el ORM). Se documenta el conteo antes de tocar nada.
        null_source_ids = (
            await session.execute(select(MarketListing.id).where(MarketListing.source.is_(None)))
        ).scalars().all()
        print(f"[apply] Filas con source=NULL detectadas: {len(null_source_ids)}")
        if null_source_ids:
            await session.execute(
                update(MarketListing).where(MarketListing.source.is_(None)).values(source="seed")
            )
            print(f"[apply]   -> backfilleadas a source='seed'.")

        # Dedup contra lo existente (seed + imports previos), misma key que el
        # dedup intra-import: direccion normalizada + m2 + precio.
        existing = (
            await session.execute(select(
                MarketListing.address, MarketListing.total_area_m2, MarketListing.price
            ))
        ).all()
        existing_keys = {
            normalize_address_key(addr, m2 or 0.0, price or 0.0)
            for addr, m2, price in existing
        }
        to_insert = []
        skipped_existing = 0
        for row in result.rows:
            key = normalize_address_key(row["address"], row["total_area_m2"], row["price"])
            if key in existing_keys:
                skipped_existing += 1
                continue
            to_insert.append(row)
        print(f"[apply] Descartadas por dedup contra existentes: {skipped_existing}")
        print(f"[apply] A insertar: {len(to_insert)}")

        # Bulk insert. NOTA performance (ver seccion 8 del reporte): para miles
        # de filas, session.execute(insert(...), to_insert) es preferible a
        # session.add_all([MarketListing(**r) for r in to_insert]) porque evita
        # crear un objeto ORM identity-mapped por fila.
        from sqlalchemy import insert
        if to_insert:
            await session.execute(insert(MarketListing), to_insert)
        await session.commit()
        print(f"[apply] OK. {len(to_insert)} filas insertadas con source='{SOURCE_TAG}'.")


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="(default) Solo parsea/mapea/reporta, no toca ninguna DB.")
    parser.add_argument("--apply", action="store_true",
                         help="Ejecuta el import real (backup + insert). Requiere DB.")
    parser.add_argument("--properties-json", type=Path, default=DEFAULT_PROPERTIES_JSON)
    parser.add_argument("--details-json", type=Path, default=DEFAULT_DETAILS_JSON)
    parser.add_argument("--sample", type=int, default=20,
                         help="Filas de diff resumido a mostrar en el dry-run.")
    parser.add_argument("--spot-check", type=int, default=5,
                         help="Filas completas mapeadas (JSON) a mostrar para validar a mano.")
    args = parser.parse_args()

    if not args.properties_json.exists():
        sys.exit(f"No existe {args.properties_json} (repo donante beykercoldwell, solo lectura)")
    if not args.details_json.exists():
        sys.exit(f"No existe {args.details_json} (repo donante beykercoldwell, solo lectura)")

    if args.apply:
        import asyncio
        confirm = input(
            "Vas a INSERTAR contra la DB configurada en backend/.env. "
            "Escribi 'CONFIRMO' para continuar: "
        )
        if confirm.strip() != "CONFIRMO":
            sys.exit("Cancelado.")
        asyncio.run(apply_import(args.properties_json, args.details_json))
        return

    # --dry-run es el default (con o sin el flag explicito).
    result = run_etl(args.properties_json, args.details_json)
    print_dry_run_report(result, sample_n=args.sample, spot_check_n=args.spot_check)


if __name__ == "__main__":
    main()
