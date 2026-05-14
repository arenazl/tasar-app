"""Estudio de Mercado (ACM) — núcleo de cálculo.

Método de homogeneización clásica:
- Cada comparable tiene su precio crudo y precio/m².
- Se le aplican coeficientes de ajuste (área, estado, antigüedad, ubicación, etc).
- El precio ajustado se pondera por similitud (peso 0..1).
- El valor sugerido es la media ponderada de precios ajustados/m² × m² de la propiedad objetivo.
- Confianza = f(cantidad de comparables, dispersión, similitud promedio).
"""
from typing import List, Tuple
import statistics


def compute_comparable_adjustment(
    base_price_per_m2: float,
    adjustments_coefficients: List[float],
) -> float:
    factor = 1.0
    for c in adjustments_coefficients:
        factor *= c
    return base_price_per_m2 * factor


def compute_similarity_weight(
    target: dict,
    comparable: dict,
) -> float:
    """Score 0..1 de similitud entre la propiedad objetivo y el comparable.

    Considera: diferencia de área, antigüedad, ambientes, distancia (si hay coords),
    estado. Cuanto más parecidos, mayor peso.
    """
    score = 1.0

    # área
    ta = (target.get("total_area_m2") or target.get("covered_area_m2") or 0) or 0
    ca = (comparable.get("total_area_m2") or comparable.get("covered_area_m2") or 0) or 0
    if ta and ca:
        diff = abs(ta - ca) / max(ta, ca)
        score *= max(0.4, 1.0 - diff)  # 40% mínimo

    # ambientes
    tr = target.get("rooms") or 0
    cr = comparable.get("rooms") or 0
    if tr and cr:
        diff = abs(tr - cr) / max(tr, cr)
        score *= max(0.6, 1.0 - diff * 0.5)

    # antigüedad
    ta_y = target.get("age_years")
    ca_y = comparable.get("age_years")
    if ta_y is not None and ca_y is not None:
        diff = abs(ta_y - ca_y)
        score *= max(0.5, 1.0 - diff / 50)

    return round(max(0.1, min(1.0, score)), 3)


def compute_market_study(
    target: dict,
    comparables: List[dict],
) -> dict:
    """Recibe propiedad objetivo + lista de comparables (cada uno con adjustments).

    comparables[i] = {
      "id": int, "price": float, "total_area_m2": float, ...,
      "adjustments": [{"coefficient": 1.05}, ...]
    }

    Devuelve dict con suggested_value_min/max/mode, confidence_score y resultados
    individuales por comparable (adjusted_price, adjusted_price_per_m2, weight).
    """
    target_area = target.get("total_area_m2") or target.get("covered_area_m2") or 0
    if not target_area or not comparables:
        return {
            "suggested_value_min": None,
            "suggested_value_max": None,
            "suggested_value_mode": None,
            "confidence_score": 0.0,
            "comparable_results": [],
        }

    results = []
    weighted_ppm2 = []  # (price_per_m2_ajustado, weight)

    for c in comparables:
        area = c.get("total_area_m2") or c.get("covered_area_m2") or 0
        if not area or not c.get("price"):
            continue

        base_ppm2 = c["price"] / area
        coefs = [a.get("coefficient", 1.0) for a in c.get("adjustments", [])]
        adjusted_ppm2 = compute_comparable_adjustment(base_ppm2, coefs)
        weight = compute_similarity_weight(target, c)

        results.append({
            "id": c.get("id"),
            "price_per_m2": round(base_ppm2, 2),
            "adjusted_price_per_m2": round(adjusted_ppm2, 2),
            "adjusted_price": round(adjusted_ppm2 * area, 2),
            "weight": weight,
        })
        weighted_ppm2.append((adjusted_ppm2, weight))

    if not weighted_ppm2:
        return {
            "suggested_value_min": None,
            "suggested_value_max": None,
            "suggested_value_mode": None,
            "confidence_score": 0.0,
            "comparable_results": [],
        }

    total_weight = sum(w for _, w in weighted_ppm2) or 1.0
    weighted_avg_ppm2 = sum(p * w for p, w in weighted_ppm2) / total_weight

    only_ppm2 = [p for p, _ in weighted_ppm2]
    min_v = min(only_ppm2) * target_area
    max_v = max(only_ppm2) * target_area
    mode_v = weighted_avg_ppm2 * target_area

    # Confianza: más comparables + menor dispersión + mayor similitud = mejor
    n = len(weighted_ppm2)
    n_factor = min(1.0, n / 5)  # con 5+ comparables ya saturás
    if n > 1:
        stdev = statistics.pstdev(only_ppm2)
        dispersion = stdev / weighted_avg_ppm2 if weighted_avg_ppm2 else 1
        disp_factor = max(0.2, 1.0 - min(1.0, dispersion))
    else:
        disp_factor = 0.5
    avg_weight = sum(w for _, w in weighted_ppm2) / n
    confidence = round(n_factor * 0.4 + disp_factor * 0.3 + avg_weight * 0.3, 3)

    return {
        "suggested_value_min": round(min_v, 2),
        "suggested_value_max": round(max_v, 2),
        "suggested_value_mode": round(mode_v, 2),
        "confidence_score": confidence,
        "comparable_results": results,
    }
