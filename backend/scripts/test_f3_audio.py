"""Test standalone del audio full-duplex (WO F3-01) — sin pytest (no esta en
requirements.txt; esta suite lo suma en F3-06 segun smoke_core.py).

Sigue el mismo patron liviano de `scripts/smoke_core.py` (Report PASS/FAIL,
sin dependencias de test-framework), pero NO vive ahi adentro para no alterar
el conteo "PASS=2" que ya reporta ese runner (regresion pura de F1/F2).

Cubre:
  [1] audio_sanitizer.sanitize_for_tts corta <<PAUSE>> y separa URLs del
      texto que va a ElevenLabs (no rompe con texto sin URLs/pause).
  [2] audio_out.synthesize_reply_audio degrada a (None, "") cuando el TTS
      devuelve None (ej. ElevenLabs 429 / sin creditos) -- el caller cae a
      texto plano sin romper el flujo. Mockeado, SIN pegarle a la red.

Uso:
    python backend/scripts/test_f3_audio.py

Exit code: 0 si no hubo ningun FAIL.
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import List
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = "PASS", "FAIL"


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""


@dataclass
class Report:
    results: List[Result] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.results.append(Result(name, status, detail))
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

    @property
    def exit_code(self) -> int:
        return 1 if any(r.status == FAIL for r in self.results) else 0

    def summary(self) -> str:
        counts = {PASS: 0, FAIL: 0}
        for r in self.results:
            counts[r.status] += 1
        return f"PASS={counts[PASS]}  FAIL={counts[FAIL]}"


def test_sanitizer_pause_marker(report: Report) -> None:
    from services.audio_sanitizer import sanitize_for_tts

    texto = "Dale, te confirmo la visita.<<PAUSE>>Te veo el jueves a las 17."
    audio_text, urls = sanitize_for_tts(texto)
    ok = "<<PAUSE>>" not in audio_text and not urls and "confirmo la visita" in audio_text and "jueves" in audio_text
    report.add(
        "[1a] sanitize_for_tts corta <<PAUSE>> sin dejar el marcador en el audio",
        PASS if ok else FAIL,
        f"audio_text={audio_text!r}",
    )


def test_sanitizer_url_cut(report: Report) -> None:
    from services.audio_sanitizer import sanitize_for_tts

    texto = "Te paso el link de la propiedad: tasar.com.ar/prop/123 para que la veas."
    audio_text, urls = sanitize_for_tts(texto)
    ok = (
        "tasar.com.ar" not in audio_text
        and len(urls) == 1
        and urls[0].startswith("https://tasar.com.ar/prop/123")
    )
    report.add(
        "[1b] sanitize_for_tts saca la URL del audio y la devuelve aparte",
        PASS if ok else FAIL,
        f"audio_text={audio_text!r} urls={urls!r}",
    )


def test_sanitizer_url_false_positive(report: Report) -> None:
    """'no.es' / 'y.eso' no son URLs -- no deben cortarse como si lo fueran."""
    from services.audio_sanitizer import sanitize_for_tts

    texto = "No es un problema, y eso lo resolvemos rapido."
    audio_text, urls = sanitize_for_tts(texto)
    ok = not urls and "No es un problema" in audio_text
    report.add(
        "[1c] sanitize_for_tts no confunde texto comun con URLs (anti falso-positivo)",
        PASS if ok else FAIL,
        f"audio_text={audio_text!r} urls={urls!r}",
    )


async def _run_tts_degradation() -> tuple[bool, str]:
    from services import audio_out

    # Mockea el ÚNICO punto de red (ElevenLabs -> Cloudinary) para simular
    # 429/sin creditos SIN pegarle a la red real (no hay API keys en este entorno).
    with patch.object(audio_out, "synthesize_to_cloudinary", new=AsyncMock(return_value=None)):
        media_url, urls_text = await audio_out.synthesize_reply_audio("Hola, ¿cómo estás?", voice_id="v1")
    ok = media_url is None and urls_text == ""
    return ok, f"media_url={media_url!r} urls_text={urls_text!r}"


def test_tts_degrades_to_text_on_failure(report: Report) -> None:
    ok, detail = asyncio.run(_run_tts_degradation())
    report.add(
        "[2] audio_out.synthesize_reply_audio degrada a (None, \"\") si el TTS falla (429/sin creditos)",
        PASS if ok else FAIL,
        detail,
    )


async def _run_tts_exception_safety() -> tuple[bool, str]:
    """Si synthesize_to_cloudinary levanta una excepcion inesperada (no solo
    devuelve None), audio_out tampoco debe romper el flujo de WhatsApp."""
    from services import audio_out

    with patch.object(audio_out, "synthesize_to_cloudinary", new=AsyncMock(side_effect=RuntimeError("boom"))):
        media_url, urls_text = await audio_out.synthesize_reply_audio("Hola de nuevo", voice_id="v1")
    ok = media_url is None and urls_text == ""
    return ok, f"media_url={media_url!r} urls_text={urls_text!r}"


def test_tts_exception_never_bubbles(report: Report) -> None:
    ok, detail = asyncio.run(_run_tts_exception_safety())
    report.add(
        "[2b] audio_out.synthesize_reply_audio nunca deja escapar una excepcion de TTS",
        PASS if ok else FAIL,
        detail,
    )


def main() -> int:
    print("=" * 70)
    print("TEST F3-01 — sanitizador <<PAUSE>>/URLs + degradacion TTS a texto")
    print("=" * 70)
    report = Report()
    test_sanitizer_pause_marker(report)
    test_sanitizer_url_cut(report)
    test_sanitizer_url_false_positive(report)
    test_tts_degrades_to_text_on_failure(report)
    test_tts_exception_never_bubbles(report)
    print("=" * 70)
    print(f"  {report.summary()}")
    print("  EXIT " + ("OK" if report.exit_code == 0 else "FAIL"))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
