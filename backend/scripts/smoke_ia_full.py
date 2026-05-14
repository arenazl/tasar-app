"""Smoke test integral de TODOS los endpoints que usan IA (Claude)."""
import httpx, sys

BASE = "http://127.0.0.1:8600/api"

def section(t):
    print(f"\n{'=' * 60}\n  {t}\n{'=' * 60}")

def main():
    section("1. LOGIN")
    r = httpx.post(f"{BASE}/auth/login", json={"email": "admin@tasar.demo", "password": "admin123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("  OK")

    section("2. AI CHAT (Tasador AI - sync)")
    try:
        r = httpx.post(f"{BASE}/ai/chat",
            headers=h, timeout=120,
            json={"message": "Decime en una sola oracion que es la homogeneizacion de comparables."}
        )
        print(f"  status: {r.status_code}")
        if r.status_code == 200:
            response_text = r.json().get("response", "")
            print(f"  response[:200]: {response_text[:200]}")
            ok = bool(response_text and "[Tasador AI" not in response_text and "[Claude" not in response_text)
            print(f"  IA REAL: {'OK' if ok else 'NO (fallback)'}")
        else:
            print(f"  FAIL: {r.text[:200]}")
    except Exception as e:
        print(f"  EXC: {type(e).__name__}: {e}")

    section("3. AI ANALYZE PROPERTY")
    props = httpx.get(f"{BASE}/properties", headers=h, timeout=30).json()
    if not props:
        print("  SKIP: no hay propiedades")
    else:
        pid = props[0]["id"]
        try:
            r = httpx.post(f"{BASE}/properties/{pid}/analyze", headers=h, timeout=300)
            print(f"  status: {r.status_code}")
            if r.status_code == 200:
                d = r.json()
                print(f"  summary: {d.get('summary', '')[:120]}")
                print(f"  segment: {d.get('market_segment')}, confidence: {d.get('ai_confidence')}")
                print(f"  highlights: {len(d.get('highlights', []))}, concerns: {len(d.get('concerns', []))}")
                ok = bool(d.get('summary') or d.get('market_segment'))
                print(f"  IA REAL: {'OK' if ok else 'NO (JSON vacio)'}")
            else:
                print(f"  FAIL: {r.text[:200]}")
        except Exception as e:
            print(f"  EXC: {type(e).__name__}: {e}")

    section("4. AI SUGGEST COMPARABLES")
    if not props:
        print("  SKIP")
    else:
        pid = props[0]["id"]
        rs = httpx.post(f"{BASE}/market-studies", headers=h,
                        json={"property_id": pid, "method": "hybrid"})
        if rs.status_code != 200:
            print(f"  FAIL crear estudio: {rs.text[:200]}")
        else:
            sid = rs.json()["id"]
            r = httpx.post(f"{BASE}/market-studies/{sid}/suggest-comparables",
                           headers=h, timeout=180)
            print(f"  status: {r.status_code}")
            if r.status_code == 200:
                d = r.json()
                print(f"  candidates_evaluated: {d['candidates_evaluated']}")
                print(f"  workspace_candidates: {d.get('workspace_candidates')}, external: {d.get('external_candidates')}")
                print(f"  ai_evaluated: {d['ai_evaluated']}")
                print(f"  suggestions: {len(d['suggestions'])}")
                ok = d.get('ai_evaluated') is True
                print(f"  IA REAL: {'OK' if ok else 'NO (fallback ranking puro)'}")
                if d['suggestions']:
                    s = d['suggestions'][0]
                    print(f"  primera: {s['candidate'].get('title')[:50]} - reason: {s.get('similarity_reason', '')[:80]}")
            else:
                print(f"  FAIL: {r.text[:200]}")

    section("5. AI SCRAPING (URL extraction)")
    test_url = "https://www.zonaprop.com.ar/propiedades/departamento-2-amb-palermo-50007899.html"  # URL de ejemplo
    try:
        r = httpx.post(f"{BASE}/scraping/extract", headers=h, timeout=60,
                       json={"url": test_url})
        print(f"  status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            extracted = d.get("extracted", {})
            print(f"  cached: {d.get('cached')}, external_listing_id: {d.get('external_listing_id')}")
            print(f"  extracted keys: {list(extracted.keys())[:8] if extracted else 'vacio'}")
            ok = bool(extracted and extracted.get('title'))
            print(f"  IA REAL: {'OK' if ok else 'NO (URL invalida o JSON vacio - esperado para URL fake)'}")
        else:
            print(f"  status no-200 (esperado para URL fake): {r.text[:150]}")
    except Exception as e:
        print(f"  EXC: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("  TODOS LOS TESTS COMPLETOS")
    print("=" * 60)

if __name__ == "__main__":
    main()
