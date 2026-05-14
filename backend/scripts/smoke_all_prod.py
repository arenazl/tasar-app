"""Smoke test del 100% de los endpoints en producción.

Probamos cada endpoint con datos válidos y reportamos OK/FAIL con detalle.
"""
import httpx
import json
import sys

BASE = "https://tasar-api-acd0705c1af9.herokuapp.com/api"
TIMEOUT = 60

results = []

def report(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    icon = "OK" if ok else "FAIL"
    print(f"  [{icon}] {name}  {detail}")


def smoke():
    # ==================== AUTH ====================
    print("\n=== AUTH ===")
    r = httpx.post(f"{BASE}/auth/login", json={"email":"admin@tasar.demo","password":"admin123"}, timeout=TIMEOUT)
    if r.status_code != 200:
        report("auth/login", False, f"HTTP {r.status_code}: {r.text[:200]}")
        return
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    report("auth/login", True, "JWT OK")

    r = httpx.get(f"{BASE}/auth/me", headers=h, timeout=TIMEOUT)
    report("auth/me", r.status_code == 200, f"user={r.json().get('email')}" if r.status_code==200 else r.text[:100])

    # ==================== DASHBOARD ====================
    print("\n=== DASHBOARD ===")
    r = httpx.get(f"{BASE}/dashboard", headers=h, timeout=TIMEOUT)
    report("dashboard", r.status_code == 200, f"kpis={len(r.json().get('kpis',[]))}" if r.status_code==200 else r.text[:100])

    # ==================== PROPIEDADES ====================
    print("\n=== PROPIEDADES ===")
    r = httpx.get(f"{BASE}/properties", headers=h, timeout=TIMEOUT)
    if r.status_code == 200:
        props = r.json()
        report("GET properties", True, f"count={len(props)}")
        if props:
            pid = props[0]["id"]
            r = httpx.get(f"{BASE}/properties/{pid}", headers=h, timeout=TIMEOUT)
            report(f"GET properties/{pid}", r.status_code == 200)
    else:
        report("GET properties", False, r.text[:100])
        props = []

    # CREATE property
    new_prop = {
        "title": "[SMOKE] Test depto", "property_type": "departamento", "operation": "venta",
        "province": "CABA", "city": "CABA", "neighborhood": "Palermo",
        "address": "Test 1234", "total_area_m2": 50, "rooms": 2, "asking_price": 100000,
    }
    r = httpx.post(f"{BASE}/properties", headers=h, json=new_prop, timeout=TIMEOUT)
    created_pid = None
    if r.status_code == 200:
        created_pid = r.json()["id"]
        report("POST properties", True, f"id={created_pid}")
    else:
        report("POST properties", False, r.text[:200])

    # UPDATE + DELETE created
    if created_pid:
        r = httpx.put(f"{BASE}/properties/{created_pid}", headers=h, json={"title":"[SMOKE] updated"}, timeout=TIMEOUT)
        report(f"PUT properties/{created_pid}", r.status_code == 200)
        r = httpx.delete(f"{BASE}/properties/{created_pid}", headers=h, timeout=TIMEOUT)
        report(f"DELETE properties/{created_pid}", r.status_code == 200)

    # ==================== APPRAISALS ====================
    print("\n=== TASACIONES ===")
    r = httpx.get(f"{BASE}/appraisals", headers=h, timeout=TIMEOUT)
    appraisals = r.json() if r.status_code == 200 else []
    report("GET appraisals", r.status_code == 200, f"count={len(appraisals)}" if r.status_code==200 else r.text[:100])

    # CREATE appraisal (con fix nuevo)
    if props:
        new_app = {"property_id": props[0]["id"], "purpose": "venta", "currency": "USD"}
        r = httpx.post(f"{BASE}/appraisals", headers=h, json=new_app, timeout=TIMEOUT)
        report("POST appraisals", r.status_code == 200, f"id={r.json().get('id')}" if r.status_code==200 else r.text[:150])

    # ==================== INBOX ====================
    print("\n=== INBOX (Bandeja) ===")
    r = httpx.get(f"{BASE}/inbox", headers=h, timeout=TIMEOUT)
    if r.status_code == 200:
        d = r.json()
        report("GET inbox", True, f"total={d['total']} unread={d['unread']}")
        if d.get("items"):
            msg_id = d["items"][0]["id"]
            r = httpx.get(f"{BASE}/inbox/{msg_id}", headers=h, timeout=TIMEOUT)
            report(f"GET inbox/{msg_id}", r.status_code == 200)
            r = httpx.post(f"{BASE}/inbox/{msg_id}/read", headers=h, timeout=TIMEOUT)
            report(f"POST inbox/{msg_id}/read", r.status_code == 200)
    else:
        report("GET inbox", False, r.text[:100])

    r = httpx.get(f"{BASE}/inbox?filter=unread", headers=h, timeout=TIMEOUT)
    report("GET inbox?filter=unread", r.status_code == 200)
    r = httpx.get(f"{BASE}/inbox?filter=assigned", headers=h, timeout=TIMEOUT)
    report("GET inbox?filter=assigned", r.status_code == 200)

    # ==================== MARKET ====================
    print("\n=== MERCADO ===")
    r = httpx.get(f"{BASE}/market/dashboard", headers=h, timeout=TIMEOUT)
    if r.status_code == 200:
        d = r.json()
        report("GET market/dashboard", True, f"index={d.get('tasar_index')} yoy={d.get('yoy_change_pct')}%")
    else:
        report("GET market/dashboard", False, r.text[:100])

    r = httpx.get(f"{BASE}/market/comparables?neighborhood=Palermo&property_type=departamento&rooms=3", headers=h, timeout=TIMEOUT)
    if r.status_code == 200:
        d = r.json()
        report("GET market/comparables", True, f"total={d['total']} median={d.get('median_ppm2')}")
    else:
        report("GET market/comparables", False, r.text[:100])

    # ==================== REPORTS ====================
    print("\n=== REPORTES ===")
    r = httpx.get(f"{BASE}/reports", headers=h, timeout=TIMEOUT)
    if r.status_code == 200:
        d = r.json()
        report("GET reports", True, f"count={len(d)}")
        if d:
            r = httpx.get(f"{BASE}/reports/{d[0]['id']}", headers=h, timeout=TIMEOUT)
            report(f"GET reports/{d[0]['id']}", r.status_code == 200)
    else:
        report("GET reports", False, r.text[:100])

    # ==================== HEATMAP ====================
    print("\n=== HEATMAP ===")
    r = httpx.get(f"{BASE}/heatmap/points", headers=h, timeout=TIMEOUT)
    report("GET heatmap/points", r.status_code == 200,
           f"count={len(r.json())}" if r.status_code==200 else r.text[:100])
    r = httpx.get(f"{BASE}/heatmap/zones", headers=h, timeout=TIMEOUT)
    report("GET heatmap/zones", r.status_code == 200)

    # ==================== SETTINGS ====================
    print("\n=== SETTINGS ===")
    r = httpx.get(f"{BASE}/settings/claude_model", headers=h, timeout=TIMEOUT)
    report("GET settings/claude_model", r.status_code == 200, f"value={r.json().get('value')}" if r.status_code==200 else "")
    r = httpx.get(f"{BASE}/settings/ai_provider", headers=h, timeout=TIMEOUT)
    report("GET settings/ai_provider", r.status_code == 200)
    r = httpx.put(f"{BASE}/settings/ai_provider", headers=h, json={"value":"gemini"}, timeout=TIMEOUT)
    report("PUT settings/ai_provider=gemini", r.status_code == 200)

    # ==================== AI (con Gemini activo) ====================
    print("\n=== AI (provider=gemini ahora) ===")
    r = httpx.post(f"{BASE}/ai/chat", headers=h, timeout=180,
                   json={"message":"Decime en 5 palabras qué es la homogeneización."})
    if r.status_code == 200:
        txt = r.json().get("response","")
        is_real = not txt.startswith("[")
        report("POST ai/chat", True, f"IA={'REAL' if is_real else 'fallback'} · {txt[:60]}")
    else:
        report("POST ai/chat", False, r.text[:200])

    r = httpx.post(f"{BASE}/ai/coach", headers=h, timeout=180, json={"route":"bandeja"})
    if r.status_code == 200:
        d = r.json()
        report("POST ai/coach", True, f"tips={len(d.get('tips',[]))} ai={d.get('generated_by_ai')}")
    else:
        report("POST ai/coach", False, r.text[:200])

    # ANALYZE
    if props:
        r = httpx.post(f"{BASE}/properties/{props[0]['id']}/analyze", headers=h, timeout=180)
        if r.status_code == 200:
            d = r.json()
            report("POST properties/{id}/analyze", True,
                   f"segment={d.get('market_segment')} conf={d.get('ai_confidence')}")
        else:
            report("POST properties/{id}/analyze", False, r.text[:200])

    # SUGGEST COMPARABLES
    if appraisals:
        ap_id = appraisals[0].get("id")
        # nuevo endpoint requiere estudio; usamos el viejo /market-studies si existe data
        r = httpx.get(f"{BASE}/market-studies", headers=h, timeout=TIMEOUT)
        if r.status_code == 200 and r.json():
            sid = r.json()[0]["id"]
            r = httpx.post(f"{BASE}/market-studies/{sid}/suggest-comparables", headers=h, timeout=180)
            if r.status_code == 200:
                d = r.json()
                report("POST market-studies/{id}/suggest-comparables", True,
                       f"sugg={len(d.get('suggestions',[]))} ai={d.get('ai_evaluated')}")
            else:
                report("POST market-studies/{id}/suggest-comparables", False, r.text[:200])

    # Restaurar provider a claude por si afecta
    httpx.put(f"{BASE}/settings/ai_provider", headers=h, json={"value":"claude"}, timeout=TIMEOUT)
    print("\n=== Restored ai_provider=claude ===")

    # ==================== COLLAB ====================
    print("\n=== COLLAB ===")
    r = httpx.get(f"{BASE}/market-studies", headers=h, timeout=TIMEOUT)
    if r.status_code == 200 and r.json():
        sid = r.json()[0]["id"]
        r = httpx.get(f"{BASE}/collaboration/{sid}/consensus", headers=h, timeout=TIMEOUT)
        report(f"GET collaboration/{sid}/consensus", r.status_code == 200)
        r = httpx.get(f"{BASE}/collaboration/{sid}/comments", headers=h, timeout=TIMEOUT)
        report(f"GET collaboration/{sid}/comments", r.status_code == 200)

    # ==================== HEALTH ====================
    print("\n=== HEALTH ===")
    r = httpx.get(f"{BASE}/health", timeout=TIMEOUT)
    report("GET health", r.status_code == 200, r.text[:50])

    # ==================== RESUMEN ====================
    print("\n" + "=" * 70)
    ok_count = sum(1 for _, ok, _ in results if ok)
    fail_count = sum(1 for _, ok, _ in results if not ok)
    print(f"  RESULTADO: {ok_count} OK · {fail_count} FAIL · {ok_count + fail_count} total")
    print("=" * 70)
    if fail_count:
        print("\nFALLOS:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}: {detail[:200]}")
    return fail_count == 0


if __name__ == "__main__":
    ok = smoke()
    sys.exit(0 if ok else 1)
