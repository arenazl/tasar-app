"""Test directo de claude_service.analyze_property y suggest_comparables — sin endpoint."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.claude_service import chat_complete, SYSTEM_ANALYZER, _extract_json


async def main():
    # 1. Analyze property — vemos el raw de Claude
    test_prop = {
        "title": "Depto Palermo 3 amb",
        "type": "departamento",
        "city": "CABA",
        "province": "CABA",
        "total_area_m2": 95,
        "covered_area_m2": 80,
        "rooms": 3,
        "age_years": 5,
        "condition": "excelente",
    }
    prompt = f"Analizá esta propiedad y devolveme el JSON estructurado.\n```json\n{json.dumps(test_prop, ensure_ascii=False, indent=2)}\n```"
    print("=== ANALYZE PROPERTY ===")
    raw = await chat_complete(prompt, system=SYSTEM_ANALYZER)
    print(f"--- raw (len={len(raw)}) ---")
    print(raw[:800])
    print("--- extracted JSON ---")
    print(json.dumps(_extract_json(raw), indent=2, ensure_ascii=False)[:600])


asyncio.run(main())
