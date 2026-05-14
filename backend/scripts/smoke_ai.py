"""Smoke test del flujo IA-first de estudios."""
import httpx, sys

BASE = "http://127.0.0.1:8600/api"

def main():
    # Login
    r = httpx.post(f"{BASE}/auth/login", json={"email": "admin@tasar.demo", "password": "admin123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Listar propiedades, agarrar la primera
    props = httpx.get(f"{BASE}/properties", headers=h).json()
    if not props:
        print("FAIL: No hay propiedades en el workspace")
        return False
    target_prop = props[0]
    print(f"Target: {target_prop['title']} ({target_prop['city']}, {target_prop['total_area_m2']}m²)")

    # Crear estudio
    r = httpx.post(f"{BASE}/market-studies", headers=h, json={
        "property_id": target_prop["id"], "method": "hybrid"
    })
    assert r.status_code == 200, r.text
    study = r.json()
    sid = study["id"]
    print(f"Estudio creado #{sid}")

    # Pedir sugerencias IA
    r = httpx.post(f"{BASE}/market-studies/{sid}/suggest-comparables", headers=h, timeout=180)
    print(f"Suggest status: {r.status_code}")
    if r.status_code != 200:
        print(f"ERROR: {r.text}")
        return False
    data = r.json()
    print(f"  candidates_evaluated: {data['candidates_evaluated']}")
    print(f"  workspace_candidates: {data.get('workspace_candidates')}")
    print(f"  external_candidates: {data.get('external_candidates')}")
    print(f"  ai_evaluated: {data['ai_evaluated']}")
    print(f"  fallback_used: {data['fallback_used']}")
    print(f"  suggestions: {len(data['suggestions'])}")
    if data.get("message"):
        print(f"  msg: {data['message']}")

    if not data["suggestions"]:
        print("FAIL: 0 sugerencias")
        return False

    # Mostrar primera sugerencia
    s = data["suggestions"][0]
    print(f"\n  Primera sugerencia:")
    print(f"    candidate_kind={s['candidate_kind']}, include={s['include']}, score={s['similarity_score']}")
    print(f"    reason: {s.get('similarity_reason', '')[:80]}")
    print(f"    candidate: {s['candidate'].get('title')} — USD {s['candidate'].get('price')}")
    print(f"    adjustments: {len(s.get('adjustments', []))}")
    for adj in s.get('adjustments', []):
        print(f"      · {adj['factor']} = {adj['coefficient']} — {adj.get('description','')[:60]}")

    # Aceptar la primera sugerencia incluida
    accepted = next((x for x in data["suggestions"] if x["include"]), None)
    if not accepted:
        print("WARN: ninguna sugerencia con include=True")
        return True

    print(f"\n  Aceptando candidate {accepted['candidate_id']}...")
    r = httpx.post(f"{BASE}/market-studies/{sid}/accept-suggestion", headers=h, json={
        "candidate_id": accepted["candidate_id"],
        "candidate_kind": accepted["candidate_kind"],
        "similarity_reason": accepted.get("similarity_reason", ""),
        "adjustments": accepted.get("adjustments", []),
    })
    if r.status_code != 200:
        print(f"  FAIL accept: {r.status_code} {r.text[:200]}")
        return False
    study2 = r.json()
    print(f"  Comparables ahora: {len(study2['comparables'])}")
    print(f"  Valor sugerido: USD {study2.get('suggested_value_mode')}")
    print(f"  Confianza: {study2.get('confidence_score')}")

    print("\nSMOKE OK")
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
