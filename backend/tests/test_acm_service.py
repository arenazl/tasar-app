"""Tests del motor ACM (services/acm_service.compute_market_study).

Puros, sin DB. El oraculo (EXPECTED / EXPECTED_WEIGHTS) es el mismo fixture
congelado que `scripts/smoke_core.py` invariante [2] -- cualquier drift
respecto de estos valores es una regresion real del calculo, no un cambio
de test. Ver el docstring de smoke_core.py para el porque del fixture.
"""
from services.acm_service import compute_market_study


def test_compute_market_study_matches_frozen_oracle():
    target = {"total_area_m2": 100, "rooms": 3, "age_years": 10}
    comparables = [
        {"id": 1, "price": 200000, "total_area_m2": 100, "rooms": 3, "age_years": 10,
         "adjustments": [{"coefficient": 1.0}]},
        {"id": 2, "price": 180000, "total_area_m2": 90, "rooms": 3, "age_years": 15,
         "adjustments": [{"coefficient": 1.05}]},
        {"id": 3, "price": 260000, "total_area_m2": 110, "rooms": 4, "age_years": 5,
         "adjustments": [{"coefficient": 0.95}]},
        {"id": 4, "price": 150000, "total_area_m2": 85, "rooms": 2, "age_years": 25,
         "adjustments": [{"coefficient": 1.1}]},
    ]

    result = compute_market_study(target, comparables)

    assert result["suggested_value_min"] == 194117.65
    assert result["suggested_value_max"] == 224545.45
    assert result["suggested_value_mode"] == 207530.41
    assert result["confidence_score"] == 0.83

    weights = {c["id"]: c["weight"] for c in result["comparable_results"]}
    assert weights == {1: 1.0, 2: 0.81, 3: 0.716, 4: 0.496}


def test_compute_market_study_no_comparables_returns_null_result():
    target = {"total_area_m2": 100, "rooms": 3, "age_years": 10}

    result = compute_market_study(target, [])

    assert result["suggested_value_min"] is None
    assert result["suggested_value_max"] is None
    assert result["suggested_value_mode"] is None
    assert result["confidence_score"] == 0.0
    assert result["comparable_results"] == []


def test_compute_market_study_no_target_area_returns_null_result():
    # Sin total_area_m2 ni covered_area_m2 no hay forma de anclar el m2 objetivo.
    target = {"rooms": 3, "age_years": 10}
    comparables = [
        {"id": 1, "price": 200000, "total_area_m2": 100, "rooms": 3, "age_years": 10,
         "adjustments": [{"coefficient": 1.0}]},
    ]

    result = compute_market_study(target, comparables)

    assert result["suggested_value_mode"] is None
    assert result["confidence_score"] == 0.0
