"""Anclaje de tasaciones al catalogo real de `market_listings` (WO F1-03).

Puerto Python del motor probado en beykercoldwell/src/lib/market-anchors.ts.
Misma logica, mismos pesos y mismos umbrales — NO se "mejoran":

- Seleccion de comparables por re-ranking de similitud. Pesos:
    superficie +/-50%  -> 0.45
    antiguedad (segun estado) -> 0.20
    features           -> 0.20
    dormitorios        -> 0.15
- Cutoff duro de superficie +/-50% para las stats; si el subset queda con <10,
  se usa todo el universo tipo+zona (mediana ruidosa evitada) — umbral 10.
- Fallback de scope: zona -> provincia -> nacional. Minimo 3 comparables por
  nivel; si <3, baja al siguiente. null si ni nacional junta 3.

El LLM (en `valuations.py`) recibe esta ancla como ground-truth y ajusta ANCLADO,
no inventa precios.

Diferencias de fuente respecto del original (adaptaciones necesarias, no mejoras):
- Fuente = tabla `market_listings` (todas las sources) en vez del JSON estatico.
- `market_listings` NO tiene columna de features estructuradas: el match de
  features se hace contra title + description (texto libre). Si no hay texto para
  matchear, el score de features cae al neutro 0.5 (igual criterio que el original
  cuando el catalogo no traia el campo).
- Ubicacion: el original hacia includes difusos sobre un unico string `location`.
  Aca `market_listings` tiene columnas province/city/neighborhood: "zona" = mismo
  city o neighborhood; "provincia" = misma province (normalizada). NOTA F0-06: la
  convencion de provincias del dataset Coldwell Banker difiere del seed, con lo
  cual el nivel "provincia" puede no matchear y caer a "nacional" — el response lo
  dice explicitamente via `scope`.
"""
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_listing import MarketListing


# Cantidad de comparables que se devuelven para el informe (top por similitud).
# El original devolvia 5; el WO F1-03 (cambio 3, PDF) pide "top 6 comparables".
# Es solo presentacion: las stats de USD/m2 se calculan sobre TODO el subset, no
# sobre estos N — cambiar 5->6 no altera los numeros del ancla.
TOP_COMPARABLES = 6

# Minimo de comparables por nivel de scope para considerarlo valido.
MIN_COMPARABLES = 3
# Umbral del subset por superficie: si el recorte +/-50% deja >= esto, las stats
# se calculan sobre el segmento similar; si no, sobre todo el universo tipo+zona.
SURFACE_SUBSET_THRESHOLD = 10
# Guarda para no traer un universo desmedido (el dataset real son cientos).
UNIVERSE_QUERY_CAP = 3000

# Mapeo estado (condition de ACM) -> rango de antiguedad esperado (anios).
# Los 4 estados del original (a estrenar/excelente/bueno/a refaccionar) mas los
# 2 extra del enum ACM (muy_bueno, a_reciclar~=a refaccionar), interpolados.
CONDITION_AGE_RANGES = {
    "a_estrenar": (0, 2),
    "excelente": (0, 10),
    "muy_bueno": (3, 20),
    "bueno": (5, 30),
    "regular": (15, 60),
    "a_reciclar": (20, 100),
}


@dataclass
class AnchorQuery:
    property_type: str
    total_area_m2: float
    province: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    condition: Optional[str] = None
    bedrooms: Optional[int] = None
    features: List[str] = field(default_factory=list)


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _quantile(sorted_vals: List[float], q: float) -> float:
    """Interpolacion lineal identica a la del original (market-anchors.ts)."""
    if not sorted_vals:
        return 0.0
    pos = (len(sorted_vals) - 1) * q
    base = int(pos)
    rest = pos - base
    if base + 1 < len(sorted_vals):
        return sorted_vals[base] + rest * (sorted_vals[base + 1] - sorted_vals[base])
    return sorted_vals[base]


def _area(m: MarketListing) -> float:
    return float(m.total_area_m2 or m.covered_area_m2 or 0.0)


def _similarity_score(m: MarketListing, q: AnchorQuery) -> float:
    """Score [0..1] de similitud del listing `m` a la propiedad evaluada `q`.

    Mismos pesos que el original: 0.45 superficie, 0.20 antiguedad, 0.20 features,
    0.15 dormitorios. Los campos ausentes en el catalogo caen al neutro 0.5 para
    no descartar comparables por falta de dato.
    """
    surf = _area(m)
    # Superficie: +/-0% -> 1, +/-50% -> 0.
    if surf and q.total_area_m2:
        surf_delta = abs(surf - q.total_area_m2) / q.total_area_m2
        surf_score = max(0.0, 1 - surf_delta / 0.5)
    else:
        surf_score = 0.0

    # Antiguedad: si el catalogo no la trae, neutro 0.5.
    age_score = 0.5
    rng = CONDITION_AGE_RANGES.get(q.condition or "")
    if m.age_years is not None and rng is not None:
        lo, hi = rng
        if lo <= m.age_years <= hi:
            age_score = 1.0
        else:
            dist = (lo - m.age_years) if m.age_years < lo else (m.age_years - hi)
            age_score = max(0.0, 1 - dist / 20)

    # Features: matcheadas contra title+description (market_listings no tiene
    # columna de features). Si no hay texto para matchear, neutro 0.5.
    feature_score = 0.5
    if q.features:
        haystack = _norm(f"{m.title or ''} {m.description or ''}")
        if haystack:
            matches = sum(1 for f in q.features if _norm(f) and _norm(f) in haystack)
            feature_score = matches / len(q.features)

    # Dormitorios: si el input no los trae, neutro 0.5.
    bed_score = 0.5
    if q.bedrooms is not None and m.bedrooms is not None:
        ref = max(q.bedrooms, 1)
        bed_score = max(0.0, 1 - abs(m.bedrooms - q.bedrooms) / ref)

    return 0.45 * surf_score + 0.20 * age_score + 0.20 * feature_score + 0.15 * bed_score


def _comparable_out(m: MarketListing) -> dict:
    area = _area(m)
    ppm2 = round(m.price / area) if (area and m.price) else None
    location = " - ".join(
        p for p in [m.neighborhood, m.city, m.province] if p
    ) or (m.address or "")
    return {
        "id": m.id,
        "title": m.title,
        "location": location,
        "surface_m2": area,
        "total_price_usd": m.price,
        "price_per_m2_usd": ppm2,
        "source": m.source,
        "source_url": m.source_url,
    }


def _build_anchor(
    matched: List[MarketListing], scope: str, property_type: str, location: str, q: AnchorQuery,
) -> Optional[dict]:
    if len(matched) < MIN_COMPARABLES:
        return None

    # 1. Cutoff duro de superficie (+/-50%). Si el segmento queda chico (<10), se
    #    ensancha la base de stats al universo completo (mediana menos ruidosa).
    in_surf = [
        m for m in matched
        if _area(m) and abs(_area(m) - q.total_area_m2) / q.total_area_m2 <= 0.5
    ] if q.total_area_m2 else []
    subset = in_surf if len(in_surf) >= SURFACE_SUBSET_THRESHOLD else matched

    # 2. Score de similitud por prop del subset, DESC.
    scored = sorted(
        ((m, _similarity_score(m, q)) for m in subset),
        key=lambda x: x[1], reverse=True,
    )

    # 3. Stats de USD/m2 sobre el subset (mismo recorte de superficie).
    ratios = sorted(
        m.price / _area(m) for m in subset if _area(m) and m.price
    )
    if not ratios:
        return None

    # 4. Top comparables por similitud.
    top = [_comparable_out(m) for m, _ in scored[:TOP_COMPARABLES]]

    return {
        "scope": scope,
        "property_type": property_type,
        "location": location,
        "count": len(subset),
        "price_per_m2": {
            "min": round(ratios[0]),
            "p25": round(_quantile(ratios, 0.25)),
            "median": round(_quantile(ratios, 0.5)),
            "p75": round(_quantile(ratios, 0.75)),
            "max": round(ratios[-1]),
        },
        "comparables": top,
    }


async def get_market_anchor(db: AsyncSession, q: AnchorQuery) -> Optional[dict]:
    """Devuelve el ancla del catalogo para la propiedad evaluada, o None si ni el
    nivel nacional junta el minimo de comparables.

    Universo: `market_listings` activos, venta, USD, del mismo tipo, con precio y
    superficie > 0. Fallback de scope zona -> provincia -> nacional.
    """
    stmt = select(MarketListing).where(
        MarketListing.status == "active",
        MarketListing.operation == "venta",
        MarketListing.currency == "USD",
        MarketListing.property_type == q.property_type,
        MarketListing.price > 0,
    ).limit(UNIVERSE_QUERY_CAP)
    rows = list((await db.execute(stmt)).scalars().all())
    # Filtro final de superficie util > 0 (no expresable trivialmente en SQL por
    # el coalesce total/covered).
    universe = [m for m in rows if _area(m) > 0]

    # --- zona: mismo city o neighborhood ---
    city_n = _norm(q.city)
    neigh_n = _norm(q.neighborhood)
    if city_n or neigh_n:
        by_zone = [
            m for m in universe
            if (city_n and _norm(m.city) == city_n) or (neigh_n and _norm(m.neighborhood) == neigh_n)
        ]
        zone_label = q.neighborhood or q.city or ""
        anchor = _build_anchor(by_zone, "zona", q.property_type, zone_label, q)
        if anchor:
            return anchor

    # --- provincia (ver NOTA F0-06 sobre convencion de provincias del dataset) ---
    prov_n = _norm(q.province)
    if prov_n:
        by_prov = [m for m in universe if _norm(m.province) == prov_n]
        anchor = _build_anchor(by_prov, "provincia", q.property_type, q.province, q)
        if anchor:
            return anchor

    # --- nacional ---
    return _build_anchor(universe, "nacional", q.property_type, "Argentina", q)


def format_anchor_for_prompt(anchor: dict) -> str:
    """Bloque de texto con el ancla para inyectar en el prompt del LLM.

    Adaptado de formatAnchorForPrompt (valuator.ts): son propiedades reales del
    catalogo, pre-filtradas por similitud; precio de PUBLICACION, no de cierre.
    """
    scope = anchor["scope"]
    loc = anchor["location"]
    ptype = anchor["property_type"]
    if scope == "zona":
        scope_label = f'zona "{loc}"'
    elif scope == "provincia":
        scope_label = f'provincia "{loc}"'
    else:
        scope_label = f"{ptype} en Argentina (sin match en zona/provincia, fallback nacional)"
    ppm2 = anchor["price_per_m2"]
    lines = [
        "## ANCLA REAL DEL CATALOGO DE MERCADO (market_listings)",
        "Estos NO son comparables hipoteticos: son propiedades publicadas en el catalogo",
        "de mercado, PRE-FILTRADAS por similitud a la propiedad evaluada (superficie +/-50%,",
        "antiguedad acorde al estado declarado, features y dormitorios similares).",
        f"Alcance del ancla: {ptype} en {scope_label} - {anchor['count']} propiedades del segmento similar.",
        "",
        "Distribucion de USD/m2 del SEGMENTO SIMILAR (precio de PUBLICACION, no de cierre):",
        f"- Min: USD {ppm2['min']:,}/m2",
        f"- P25: USD {ppm2['p25']:,}/m2",
        f"- Mediana: USD {ppm2['median']:,}/m2",
        f"- P75: USD {ppm2['p75']:,}/m2",
        f"- Max: USD {ppm2['max']:,}/m2",
        "",
        "Top comparables del catalogo (ordenados por similitud, precio de publicacion):",
    ]
    for i, c in enumerate(anchor["comparables"], 1):
        ppm2_c = f"{c['price_per_m2_usd']:,}" if c["price_per_m2_usd"] else "?"
        total_c = f"{c['total_price_usd']:,.0f}" if c["total_price_usd"] else "?"
        lines.append(
            f"{i}. {c['title']} - {c['location']} - {c['surface_m2']:.0f} m2 - "
            f"USD {total_c} ({ppm2_c} USD/m2)"
        )
    return "\n".join(lines)
