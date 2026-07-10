"""Refresh del dataset Coldwell Banker Argentina -> market_listings (WO F3-04).

Depende de: import_cb_dataset.py (WO F0-06) -- este script SOLO agrega la
etapa de scraping (listado + detalle) y despues reusa el ETL de F0-06 tal
cual (mapeo, sanidad, dedup) pasandole un `source_tag` con la fecha del
refresh, para dejar provenance de cuando entro cada fila.

Port a Python de los scrapers de beykercoldwell (repo donante, SOLO LECTURA):
  - scripts/scrape-cb-argentina.mjs  -> etapa "list"    (listado paginado)
  - scripts/scrape-details.mjs       -> etapa "details" (ficha por propiedad)

Por que portar a Python en vez de invocar el .mjs con `node`: el sitio de CB
(Brokian) es HTML server-rendered -- ambos scrapers originales usan `fetch()`
plano + regex sobre el HTML, SIN Playwright ni ejecucion de JS. No hay ninguna
razon para cargar un runtime Node dentro de la imagen del backend solo para
esto; portear a httpx es mas robusto (mismo runtime que ya corre la app, sin
proceso hijo, sin depender de que `node` este en el PATH del contenedor) y
evita agregarle a la imagen Docker un segundo lenguaje.

Reglas duras respetadas:
  - Nunca se inventa un dato: si un campo no aparece en el HTML, queda ausente
    (igual que el .mjs original) y el ETL de F0-06 ya excluye filas sin los
    campos obligatorios (precio, superficie, tipo soportado, etc).
  - El refresh es MANUAL (lo corre el dueno/Infra). No hay cron desde este WO
    -- ver nota en backend/README.md.
  - --apply requiere backend/.env con credenciales reales; el default es
    --dry-run (no toca ninguna DB), igual que import_cb_dataset.py.

Uso (desde `backend/`):
    # 1) Scrapear listado + detalles a JSON local (resumable, no toca DB):
    python scripts/refresh_cb_dataset.py --stage all

    # 2) Ver el reporte del ETL sobre lo recien scrapeado (dry-run, default):
    python scripts/refresh_cb_dataset.py --stage none

    # 3) Importar de verdad (backup + insert incremental, pide confirmacion):
    python scripts/refresh_cb_dataset.py --stage none --apply

    # Self-test 100% offline del dedup incremental (sin red, sin DB):
    python scripts/refresh_cb_dataset.py --dedup-selftest

Exit code de --dedup-selftest: 0 si no hubo ningun FAIL.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import import_cb_dataset as etl  # noqa: E402  (mismo directorio; ver sys.path arriba)

# ============================================================================
# Constantes
# ============================================================================

BASE = "https://coldwellbanker.com.ar"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Salida del refresh: JSON propios de ESTE repo (nunca se escribe en el repo
# donante beykercoldwell, que es solo-lectura). No versionado -- ver .gitignore.
OUT_DIR = Path(__file__).parent / "_cb_refresh"
PROPERTIES_OUT = OUT_DIR / "cb-argentina.json"
DETAILS_OUT = OUT_DIR / "cb-argentina-details.json"

REQUEST_TIMEOUT_S = 30
DETAIL_TIMEOUT_S = 25
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_S = 1.5
CONSECUTIVE_EMPTY_STOP = 3
SAVE_EVERY_S = 10


# ============================================================================
# Helpers de texto (port 1:1 de decode()/stripTags() del .mjs)
# ============================================================================

_ENTITY_MAP = [
    ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
    ("&nbsp;", " "),
    ("&aacute;", "á"), ("&eacute;", "é"), ("&iacute;", "í"),
    ("&oacute;", "ó"), ("&uacute;", "ú"), ("&ntilde;", "ñ"),
    ("&Aacute;", "Á"), ("&Eacute;", "É"), ("&Iacute;", "Í"),
    ("&Oacute;", "Ó"), ("&Uacute;", "Ú"), ("&Ntilde;", "Ñ"),
]
_WS_COLLAPSE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")


def decode(s: str | None) -> str:
    if not s:
        return ""
    out = s
    for src, dst in _ENTITY_MAP:
        out = out.replace(src, dst)
    out = _WS_COLLAPSE_RE.sub(" ", out).strip()
    return out


def strip_tags(s: str | None) -> str:
    return decode(_TAG_RE.sub(" ", str(s or "")))


# ============================================================================
# Etapa "list": parseo de una pagina de /propiedades?page=N
# (port 1:1 de parseListPage() en scrape-cb-argentina.mjs)
# ============================================================================

_CARD_RE = re.compile(r'data-id="(\d+)"\s+data-type="([^"]+)"')
_LDJSON_RE = re.compile(r'<script[^>]*application/ld\+json[^>]*>\s*([\s\S]*?)\s*</script>')
_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"')
_OPERACION_RE = re.compile(r"Precio de (venta|alquiler|reserva|alquiler temporario)", re.I)
_LOCATION_RE = re.compile(r'<p[^>]*class="description"[^>]*>\s*Argentina[,\s]*([^<]+?)\s*</p>', re.I)
_LI_RE = re.compile(r"<li>([\s\S]*?)</li>")
_DORM_RE = re.compile(r"(\d+)\s*Dormitori", re.I)
_BATH_RE = re.compile(r"(\d+)\s*Ba(?:ñ|n)o", re.I)
_M2_RES = [
    re.compile(r"(\d+(?:[.,]\d+)?)\s*m\s*2", re.I),
    re.compile(r"(\d+(?:[.,]\d+)?)\s*m²", re.I),
    re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*m\s*$", re.I),
]
_REF_RE = re.compile(r"^[A-Z]{2,4}\d{4,}$")


def parse_list_page(html: str, page_url: str) -> list[dict]:
    out: list[dict] = []
    positions = [(m.group(1), m.group(2), m.start()) for m in _CARD_RE.finditer(html)]

    for i, (prop_id, prop_type, idx) in enumerate(positions):
        next_idx = positions[i + 1][2] if i + 1 < len(positions) else len(html)
        card = html[idx:next_idx]

        ld: dict | None = None
        ld_match = _LDJSON_RE.search(card)
        if ld_match:
            try:
                ld = json.loads(ld_match.group(1))
            except (json.JSONDecodeError, ValueError):
                ld = None

        title = strip_tags(ld.get("name")) if ld and ld.get("name") else ""
        description = strip_tags(ld.get("description")) if ld and ld.get("description") else ""
        detail_url = (ld or {}).get("url") or ""
        img_match = _IMG_RE.search(card)
        image = (ld or {}).get("image") or (img_match.group(1) if img_match else "")

        offers = (ld or {}).get("offers") or {}
        price_value = float(offers["price"]) if offers.get("price") is not None else None
        price_currency = offers.get("priceCurrency") or ""
        price_valid_until = offers.get("priceValidUntil") or ""

        operacion_match = _OPERACION_RE.search(card)
        operacion = operacion_match.group(1).lower() if operacion_match else ""

        loc_match = _LOCATION_RE.search(card)
        location = strip_tags(loc_match.group(1)) if loc_match else ""

        li_items = [strip_tags(m.group(1)) for m in _LI_RE.finditer(card)]
        bedrooms = bathrooms = surface_m2 = None
        reference = ""
        for text in li_items:
            dorm = _DORM_RE.search(text)
            if dorm:
                bedrooms = int(dorm.group(1))
                continue
            bath = _BATH_RE.search(text)
            if bath:
                bathrooms = int(bath.group(1))
                continue
            m2_val = None
            for m2_rx in _M2_RES:
                m2_match = m2_rx.search(text)
                if m2_match:
                    m2_val = float(m2_match.group(1).replace(",", "."))
                    break
            if m2_val is not None:
                surface_m2 = m2_val
                continue
            if _REF_RE.match(text):
                reference = text
                continue

        out.append({
            "id": prop_id,
            "type": prop_type,
            "title": title,
            "description": description,
            "location": location,
            "operacion": operacion,
            "priceCurrency": price_currency,
            "priceValue": price_value,
            "priceValidUntil": price_valid_until,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "surfaceM2": surface_m2,
            "reference": reference,
            "image": image,
            "detailUrl": detail_url,
            "sourcePage": page_url,
        })
    return out


# ============================================================================
# Etapa "details": parseo de una ficha de detalle
# (port 1:1 de parseDetail() en scrape-details.mjs)
# ============================================================================

_DETAIL_FIELDS = [
    "area", "code", "type", "floors", "bedrooms", "antiquity",
    "bathrooms", "situation", "orientation", "amenities", "expenses",
]
_BOLD_LABEL_RE = re.compile(r"<b[^>]*>[^<]+</b>", re.I)
_GEO_RE = re.compile(r'data-lat="(-?\d+\.\d+)"[^>]*data-lng="(-?\d+\.\d+)"')
_MAPS_EMBED_RE = re.compile(r"maps/embed/v1/place[^\"]*q=(-?\d+\.\d+),(-?\d+\.\d+)")
_CITY_RE = re.compile(r'<span\s+class="city[^"]*"[^>]*>\s*([^<]+?)\s*</span>', re.I)
_PROVINCE_RE = re.compile(r'<span\s+class="province[^"]*"[^>]*>\s*([^<]+?)\s*</span>', re.I)
_ADDR_BLOCK_RE = re.compile(r'<p\s+class="map-location"[^>]*>([\s\S]*?)</p>', re.I)
_ADDR_STRIP_I_RE = re.compile(r"<i[^>]*>[\s\S]*?</i>", re.I)
_ADDR_STRIP_SPAN_RE = re.compile(r"<span[^>]*>[\s\S]*?</span>", re.I)
_ESTRENAR_RE = re.compile(r"estrenar|en pozo|en construccion")
_DIGITS_RE = re.compile(r"(\d{1,3})")


def _detail_field_re(field: str) -> re.Pattern:
    return re.compile(
        rf'<li[^>]*class="[^"]*\b{re.escape(field)}\b[^"]*"[^>]*>([\s\S]*?)</li>', re.I
    )


def _strip_accents(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def parse_detail(html: str) -> dict:
    out: dict[str, Any] = {}
    for field in _DETAIL_FIELDS:
        m = _detail_field_re(field).search(html)
        if m:
            inner = _BOLD_LABEL_RE.sub("", m.group(1), count=1)
            val = strip_tags(inner)
            if val:
                out[field] = val

    geo = _GEO_RE.search(html)
    if geo:
        out["lat"] = float(geo.group(1))
        out["lng"] = float(geo.group(2))
    else:
        maps_url = _MAPS_EMBED_RE.search(html)
        if maps_url:
            out["lat"] = float(maps_url.group(1))
            out["lng"] = float(maps_url.group(2))

    city_match = _CITY_RE.search(html)
    if city_match:
        out["city"] = strip_tags(city_match.group(1))
    prov_match = _PROVINCE_RE.search(html)
    if prov_match:
        out["province"] = strip_tags(prov_match.group(1))

    addr_match = _ADDR_BLOCK_RE.search(html)
    if addr_match:
        inner = _ADDR_STRIP_I_RE.sub("", addr_match.group(1))
        inner = _ADDR_STRIP_SPAN_RE.sub("", inner)
        addr = strip_tags(inner)
        if addr:
            out["address"] = addr

    if out.get("antiquity"):
        t = _strip_accents(out["antiquity"].lower())
        if _ESTRENAR_RE.search(t):
            out["antiguedadYears"] = 0
        else:
            m = _DIGITS_RE.search(t)
            if m:
                y = int(m.group(1))
                if 0 <= y <= 200:
                    out["antiguedadYears"] = y

    return out


# ============================================================================
# Fetch con reintentos (port de fetchPage()/fetchDetail() del .mjs)
# ============================================================================

async def _fetch_html(client, url: str, timeout_s: int, referer: str) -> str | None:
    import httpx

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            res = await client.get(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-AR,es;q=0.9",
                    "Referer": referer,
                },
                timeout=timeout_s,
                follow_redirects=True,
            )
            res.raise_for_status()
            return res.text
        except (httpx.HTTPError, httpx.TimeoutException) as err:
            if attempt < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_S * attempt)
                continue
            print(f"[refresh] FAILED {url}: {err}")
            return None
    return None


async def _pool(items: list, concurrency: int, worker) -> list:
    """Equivalente al pool() del .mjs: N workers consumiendo de una cola compartida."""
    sem = asyncio.Semaphore(concurrency)

    async def run_one(item):
        async with sem:
            return await worker(item)

    return await asyncio.gather(*(run_one(it) for it in items))


# ============================================================================
# Etapa "list": scrapea /propiedades?page=N hasta vaciarse
# ============================================================================

async def scrape_list(
    max_page: int, start_page: int, concurrency: int, out_path: Path
) -> Path:
    import httpx

    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing_props: list[dict] = []
    seen_ids: set[str] = set()
    if out_path.exists():
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            existing_props = data.get("properties", [])
            seen_ids = {p["id"] for p in existing_props}
        except (json.JSONDecodeError, OSError):
            pass

    all_props = list(existing_props)
    print(f"[refresh:list] resuming with {len(existing_props)} known properties")

    t0 = time.monotonic()
    last_saved = time.monotonic()
    consecutive_empty = 0

    def _save():
        out_path.write_text(
            json.dumps(
                {
                    "scrapedAt": datetime.now(timezone.utc).isoformat(),
                    "source": BASE,
                    "total": len(all_props),
                    "properties": all_props,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    async with httpx.AsyncClient() as client:
        page = start_page
        while page <= max_page:
            batch = list(range(page, min(page + concurrency, max_page + 1)))

            async def fetch_one(p):
                url = f"{BASE}/propiedades?page={p}"
                html = await _fetch_html(client, url, REQUEST_TIMEOUT_S, BASE + "/")
                if html is None:
                    return p, [], False
                return p, parse_list_page(html, url), True

            results = await _pool(batch, concurrency, fetch_one)
            batch_added = 0
            for p, props, ok in results:
                if not ok:
                    consecutive_empty += 1
                    continue
                if not props:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0
                for prop in props:
                    if prop["id"] not in seen_ids:
                        seen_ids.add(prop["id"])
                        all_props.append(prop)
                        batch_added += 1

            elapsed = time.monotonic() - t0
            print(
                f"[refresh:list] pages {batch[0]}..{batch[-1]} | +{batch_added} new | "
                f"total={len(all_props)} | {elapsed:.1f}s"
            )

            if time.monotonic() - last_saved > SAVE_EVERY_S or batch_added > 0:
                _save()
                last_saved = time.monotonic()

            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                print(f"[refresh:list] {CONSECUTIVE_EMPTY_STOP} paginas vacias seguidas -- corto en page {batch[-1]}")
                break

            page += concurrency

    _save()
    print(f"[refresh:list] DONE -- {len(all_props)} propiedades -> {out_path}")
    return out_path


# ============================================================================
# Etapa "details": ficha por propiedad (resumible)
# ============================================================================

async def scrape_details(
    properties_path: Path, concurrency: int, limit: int | None, out_path: Path
) -> Path:
    import httpx

    out_path.parent.mkdir(parents=True, exist_ok=True)
    props = json.loads(properties_path.read_text(encoding="utf-8")).get("properties", [])
    if limit:
        props = props[:limit]

    details: dict[str, dict] = {}
    if out_path.exists():
        try:
            details = json.loads(out_path.read_text(encoding="utf-8")).get("details", {})
        except (json.JSONDecodeError, OSError):
            details = {}

    todo = [p for p in props if p.get("detailUrl") and p["id"] not in details]
    print(f"[refresh:details] total={len(props)} | already_done={len(details)} | todo={len(todo)}")

    t0 = time.monotonic()
    last_saved = time.monotonic()
    done = 0

    def _save():
        out_path.write_text(
            json.dumps(
                {"scrapedAt": datetime.now(timezone.utc).isoformat(), "details": details},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    async with httpx.AsyncClient() as client:
        async def fetch_one(prop):
            nonlocal done, last_saved
            html = await _fetch_html(client, prop["detailUrl"], DETAIL_TIMEOUT_S, BASE + "/")
            if html is not None:
                details[prop["id"]] = parse_detail(html)
            else:
                details[prop["id"]] = {"error": "fetch_failed"}
            done += 1
            if done % 50 == 0:
                pct = 100 * done / len(todo) if todo else 100
                print(f"[refresh:details] {done}/{len(todo)} ({pct:.1f}%)")
            if time.monotonic() - last_saved > SAVE_EVERY_S:
                _save()
                last_saved = time.monotonic()

        await _pool(todo, concurrency, fetch_one)

    _save()
    elapsed = time.monotonic() - t0
    with_age = sum(1 for d in details.values() if d.get("antiguedadYears") is not None)
    print(f"[refresh:details] DONE -- {len(details)} fichas | con antiguedad: {with_age} | {elapsed:.1f}s")
    return out_path


# ============================================================================
# Self-test 100% offline del dedup incremental (sin red, sin DB)
# Sigue el patron liviano de scripts/test_notify_f3_03.py (Report PASS/FAIL).
# ============================================================================

def _fixture_prop(prop_id: str, price: float, surface: float, ref: str) -> dict:
    return {
        "id": prop_id, "type": "Departamento", "title": f"Depto {prop_id}",
        "description": "Luminoso con balcon", "location": "", "operacion": "venta",
        "priceCurrency": "USD", "priceValue": price, "priceValidUntil": "",
        "bedrooms": 2, "bathrooms": 1, "surfaceM2": surface, "reference": ref,
        "image": "https://x/img.jpg", "detailUrl": f"https://x/{prop_id}", "sourcePage": "",
    }


def _fixture_detail(province: str, city: str, address: str, lat: float, lng: float) -> dict:
    return {"province": province, "city": city, "address": address, "lat": lat, "lng": lng}


def run_dedup_selftest() -> int:
    """Prueba (sin red, sin DB) que:
    [1] run_etl deduplica dentro del propio batch (direccion+m2+precio).
    [2] filter_new_rows, corrido 2 veces con el MISMO existing_keys que
        resultaria de haber importado el batch la primera vez, no vuelve a
        insertar nada en la segunda corrida -- que es exactamente lo que
        pasa cuando el dueno corre el refresh 2 veces sobre el mismo scrape.
    """
    import tempfile

    PASS, FAIL = "PASS", "FAIL"
    results: list[tuple[str, str, str]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        status = PASS if cond else FAIL
        results.append((name, status, detail))
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        props_path = tmp_path / "props.json"
        details_path = tmp_path / "details.json"

        # 3 propiedades: 2 y 3 son un duplicado exacto (misma direccion+m2+precio,
        # id distinto -- exactamente lo que produce un re-scrape del mismo listado).
        properties = [
            _fixture_prop("1001", 120000, 55, "CB0001"),
            _fixture_prop("1002", 95000, 40, "CB0002"),
            _fixture_prop("1003", 95000, 40, "CB0003"),  # dup de 1002
        ]
        details = {
            "1001": _fixture_detail("CABA", "Palermo", "Av. Santa Fe 3000", -34.58, -58.42),
            "1002": _fixture_detail("CABA", "Recoleta", "Av. Callao 1500", -34.60, -58.39),
            "1003": _fixture_detail("CABA", "Recoleta", "Av. Callao 1500", -34.60, -58.39),
        }
        props_path.write_text(json.dumps({"properties": properties}), encoding="utf-8")
        details_path.write_text(json.dumps({"details": details}), encoding="utf-8")

        source_tag = f"cb-argentina-{date.today():%Y-%m-%d}"

        # [1] Dedup intra-batch: de 3 filas validas, 1 se cae por duplicado.
        result = etl.run_etl(props_path, details_path, source_tag=source_tag)
        check(
            "run_etl dedupe intra-batch (3 filas -> 2 unicas)",
            len(result.rows) == 2 and result.dup_dropped == 1,
            f"rows={len(result.rows)} dup_dropped={result.dup_dropped}",
        )
        check(
            "filas mapeadas llevan el source_tag del refresh (provenance)",
            all(r["source"] == source_tag for r in result.rows),
            f"source_tag={source_tag}",
        )

        # [2] Simulo: la 1ra corrida del refresh importa result.rows (existing_keys
        # queda vacio -> todo entra). Calculo el mismo existing_keys que quedaria
        # en la DB despues de esa 1ra corrida.
        existing_keys_before: set[str] = set()
        to_insert_1, skipped_1 = etl.filter_new_rows(result.rows, existing_keys_before)
        check(
            "1ra corrida: existing vacio -> inserta las 2 filas unicas",
            len(to_insert_1) == 2 and skipped_1 == 0,
            f"to_insert={len(to_insert_1)} skipped={skipped_1}",
        )

        existing_keys_after = {
            etl.normalize_address_key(r["address"], r["total_area_m2"], r["price"])
            for r in to_insert_1
        }

        # Corro el ETL una 2da vez sobre el MISMO scrape (simula "el dueno corrio
        # el refresh 2 veces") y filtro contra lo que ya quedo en existing_keys.
        result_2 = etl.run_etl(props_path, details_path, source_tag=source_tag)
        to_insert_2, skipped_2 = etl.filter_new_rows(result_2.rows, existing_keys_after)
        check(
            "2da corrida sobre el MISMO scrape: 0 filas nuevas, 2 descartadas por dedup",
            len(to_insert_2) == 0 and skipped_2 == 2,
            f"to_insert={len(to_insert_2)} skipped={skipped_2}",
        )

    fail_count = sum(1 for _, status, _ in results if status == FAIL)
    print(f"\nSummary: PASS={len(results) - fail_count}  FAIL={fail_count}")
    return 1 if fail_count else 0


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", choices=["all", "list", "details", "none"], default="all",
                         help="Que etapa de scraping correr. 'none' salta el scraping y solo corre el ETL "
                              "sobre lo que ya haya en _cb_refresh/ (util para re-generar el reporte o --apply).")
    parser.add_argument("--max-page", type=int, default=1000)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--details-concurrency", type=int, default=6)
    parser.add_argument("--limit-details", type=int, default=None,
                         help="Tope de fichas de detalle a scrapear (para pruebas rapidas).")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--apply", action="store_true",
                         help="Ejecuta el import real (backup + insert incremental). Requiere backend/.env.")
    parser.add_argument("--dedup-selftest", action="store_true",
                         help="Corre el self-test offline del dedup incremental (sin red, sin DB) y sale.")
    args = parser.parse_args()

    if args.dedup_selftest:
        sys.exit(run_dedup_selftest())

    properties_path = args.out_dir / "cb-argentina.json"
    details_path = args.out_dir / "cb-argentina-details.json"

    if args.stage in ("all", "list"):
        asyncio.run(scrape_list(args.max_page, args.start_page, args.concurrency, properties_path))
    if args.stage in ("all", "details"):
        if not properties_path.exists():
            sys.exit(f"No existe {properties_path} -- corre --stage list primero.")
        asyncio.run(scrape_details(properties_path, args.details_concurrency, args.limit_details, details_path))

    if not properties_path.exists() or not details_path.exists():
        sys.exit(f"Faltan {properties_path} y/o {details_path} -- corre con --stage all primero.")

    source_tag = f"cb-argentina-{date.today():%Y-%m-%d}"

    if args.apply:
        confirm = input(
            f"Vas a INSERTAR (source='{source_tag}') contra la DB configurada en backend/.env. "
            "Escribi 'CONFIRMO' para continuar: "
        )
        if confirm.strip() != "CONFIRMO":
            sys.exit("Cancelado.")
        asyncio.run(etl.apply_import(properties_path, details_path, source_tag=source_tag))
        return

    result = etl.run_etl(properties_path, details_path, source_tag=source_tag)
    etl.print_dry_run_report(result, sample_n=20, spot_check_n=5)


if __name__ == "__main__":
    main()
