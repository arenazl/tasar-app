"""Smoke test sincrono de los endpoints criticos."""
import httpx

BASE = "http://127.0.0.1:8600/api"


def main():
    results = []
    # Login
    r = httpx.post(f"{BASE}/auth/login", json={"email": "admin@tasar.demo", "password": "admin123"})
    assert r.status_code == 200, f"login fallo: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    results.append(("auth/login", r.status_code, "OK"))

    # /me
    r = httpx.get(f"{BASE}/auth/me", headers=h)
    results.append(("auth/me", r.status_code, r.json().get("full_name")))

    # Properties
    r = httpx.get(f"{BASE}/properties", headers=h)
    results.append(("GET properties", r.status_code, f"count={len(r.json())}"))

    # Dashboard
    r = httpx.get(f"{BASE}/dashboard", headers=h)
    d = r.json()
    results.append(("dashboard", r.status_code, f"kpis={len(d.get('kpis',[]))}"))

    # Heatmap
    r = httpx.get(f"{BASE}/heatmap/points", headers=h)
    results.append(("heatmap/points", r.status_code, f"count={len(r.json())}"))

    r = httpx.get(f"{BASE}/heatmap/zones", headers=h)
    results.append(("heatmap/zones", r.status_code, f"count={len(r.json())}"))

    # Crear estudio para la primera propiedad
    props = httpx.get(f"{BASE}/properties", headers=h).json()
    if props:
        pid = props[0]["id"]
        r = httpx.post(f"{BASE}/market-studies", headers=h, json={
            "property_id": pid, "method": "homogenization"
        })
        results.append(("POST market-study", r.status_code, f"id={r.json().get('id')}"))
        if r.status_code == 200:
            sid = r.json()["id"]
            # Agregar 2 comparables
            for i, price in enumerate([195000, 235000]):
                cr = httpx.post(f"{BASE}/market-studies/{sid}/comparables", headers=h, json={
                    "title": f"Comparable demo {i+1}",
                    "total_area_m2": 90 + i*10,
                    "rooms": 3,
                    "age_years": 8 + i*5,
                    "price": price,
                    "currency": "USD",
                })
                results.append((f"  add comparable {i+1}", cr.status_code, "OK" if cr.status_code == 200 else cr.text[:80]))

            rr = httpx.post(f"{BASE}/market-studies/{sid}/recalc", headers=h)
            results.append(("recalc study", rr.status_code,
                            f"valor={rr.json().get('suggested_value_mode')} conf={rr.json().get('confidence_score')}"))

    # Collaboration consensus
    r = httpx.get(f"{BASE}/collaboration/1/consensus", headers=h)
    results.append(("consensus", r.status_code, f"participants={r.json().get('participants')}"))

    print("\n=== SMOKE TEST RESULTS ===")
    all_ok = True
    for name, code, info in results:
        ok = 200 <= code < 300
        if not ok:
            all_ok = False
        print(f"  [{'OK' if ok else 'FAIL'}] {code}  {name}  -> {info}")
    print("===")
    print("RESULT:", "ALL PASSED" if all_ok else "SOME FAILED")
    return all_ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
