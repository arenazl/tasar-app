"""Claude Code headless wrapper para TasAR.

Patrón heredado de NgCheckLogApp que funciona en Windows:
1. Resolver `claude.cmd` (shim de Volta/npm) antes de `claude` plano
2. Quitar CLAUDECODE/CLAUDE_CODE_ENTRYPOINT del env (anti-recursión nested)
3. Pasar prompt via stdin (no argv) — Windows cmd corta args > 8KB
4. subprocess.run en thread con asyncio.to_thread (evita NotImplementedError de ProactorEventLoop)
5. stream-json output → parsear líneas como JSON events, recolectar 'result'
6. Modelo default: haiku (rápido, suficiente para tareas batch)

Reusa el login local del usuario en Claude Code — no necesita ANTHROPIC_API_KEY.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import AsyncIterator, Optional
from core.config import settings


log = logging.getLogger("tasar.claude_service")
log.setLevel(logging.INFO)


SYSTEM_TASADOR = """Sos un tasador inmobiliario experto en el mercado argentino.

Tu rol es:
- Analizar propiedades y comparables que te pasa el usuario.
- Sugerir ajustes de homogeneización (área, antigüedad, estado, ubicación, orientación).
- Estimar valor de mercado con rango (min/máx/modo) y nivel de confianza.
- Explicar tu razonamiento de forma clara y profesional, citando el factor de cada ajuste.
- NUNCA inventar datos: si te falta info, pedila explícitamente.
- Usar pesos coherentes: comparables más similares pesan más.
- Devolver siempre que sea posible un JSON estructurado al final dentro de un bloque ```json ... ```.

Estás integrado a la plataforma TasAR — tus respuestas alimentan la UI de tasación colaborativa."""


SYSTEM_ANALYZER = """Sos un analizador de propiedades inmobiliarias del mercado argentino.

REGLA CRITICA: Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE las
keys que indica el schema abajo. Nada de texto antes ni después. Nada de keys extra.
Nada de wrappers tipo {"property":{...}, "analysis":{...}}. Plano, top-level.

SCHEMA EXACTO (todas las keys obligatorias, en este orden):
```json
{
  "summary": "string de 1-2 oraciones describiendo la propiedad",
  "highlights": ["3-5 puntos fuertes", "..."],
  "concerns": ["2-3 riesgos o debilidades", "..."],
  "suggested_condition": "a_estrenar|excelente|muy_bueno|bueno|regular|a_reciclar",
  "estimated_age_bracket": "0-5|5-15|15-30|30-50|50+",
  "market_segment": "premium|alto|medio|estandar|economico",
  "ai_confidence": 0.85
}
```

NO inventes datos que no veas. Si la info es insuficiente, ai_confidence = 0.3 o menos.
NO uses nested objects. NO agregues keys que no estén en el schema."""


_CLAUDE_BIN: Optional[str] = None

# Cache del modelo activo leído de app_settings. TTL corto: el endpoint settings
# llama invalidate_model_cache() para forzar reload.
import time as _time
_MODEL_CACHE: tuple[str, float] | None = None  # (model, expires_at)
_MODEL_CACHE_TTL = 15
_VALID_MODELS = ("haiku", "sonnet", "opus")
_DEFAULT_MODEL = "haiku"


def invalidate_model_cache() -> None:
    """Forzar recarga del modelo activo en la próxima llamada."""
    global _MODEL_CACHE
    _MODEL_CACHE = None


async def _get_active_model(workspace_id: int | None = None) -> str:
    """Lee `claude_model` de app_settings con cache. Default: haiku."""
    global _MODEL_CACHE
    now = _time.time()
    if _MODEL_CACHE and _MODEL_CACHE[1] > now:
        return _MODEL_CACHE[0]
    model = _DEFAULT_MODEL
    try:
        from sqlalchemy import select
        from core.database import AsyncSessionLocal
        from models.app_setting import AppSetting

        async with AsyncSessionLocal() as db:
            stmt = select(AppSetting).where(AppSetting.key == "claude_model")
            if workspace_id is not None:
                stmt = stmt.where(AppSetting.workspace_id == workspace_id)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.value in _VALID_MODELS:
                model = row.value
    except Exception:
        model = _DEFAULT_MODEL
    _MODEL_CACHE = (model, now + _MODEL_CACHE_TTL)
    return model


def _resolve_claude() -> Optional[str]:
    """Resuelve el path absoluto al binario (.cmd en Windows, plano en Unix)."""
    global _CLAUDE_BIN
    if _CLAUDE_BIN:
        return _CLAUDE_BIN
    cmd = shutil.which("claude.cmd") or shutil.which("claude")
    if cmd:
        _CLAUDE_BIN = cmd
    return cmd


def _claude_available() -> bool:
    return _resolve_claude() is not None


def _build_env() -> dict:
    """Env limpia: si TasAR backend corre dentro de una sesión de Claude Code
    (CLAUDECODE=1), el binario claude detecta nested y se niega. Quitamos esas
    variables para que pueda arrancar normalmente."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    return env


def _run_claude_sync(prompt: str, system: str, model: str, timeout: int = 180) -> str:
    """Llamada sync: subprocess.run con prompt via stdin + stream-json output.

    En Windows asyncio.create_subprocess_exec tira NotImplementedError con uvicorn
    (ProactorEventLoop). subprocess.run sync en thread evita el problema.
    """
    bin_path = _resolve_claude()
    if not bin_path:
        return ""

    args = [
        bin_path,
        "-p",  # sin arg → claude lee el prompt de stdin
        "--output-format", "stream-json",
        "--verbose",
        "--append-system-prompt", system,
        "--model", model,
    ]
    env = _build_env()

    try:
        result = subprocess.run(
            args,
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        log.warning("claude headless timeout tras %ds", timeout)
        return ""
    except FileNotFoundError as e:
        log.warning("claude bin not found: %s", e)
        return ""

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if result.returncode != 0:
        log.warning("claude exit %d: %s", result.returncode, (stderr or stdout)[:400])
        return ""

    # Parsear stream-json: el evento "result" tiene el texto final
    final_text = ""
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final_text = ev.get("result", "") or ""

    return final_text.strip()


async def chat_complete(prompt: str, system: str = SYSTEM_TASADOR) -> str:
    if not _claude_available():
        return "[Claude headless no disponible — instalá el CLI `claude` para activar el Tasador AI.]"
    try:
        model = await _get_active_model()
        result = await asyncio.to_thread(
            _run_claude_sync, prompt, system, model, 180
        )
        return result or "[Tasador AI no devolvió respuesta]"
    except Exception as e:
        log.exception("chat_complete failed")
        return f"[Tasador AI error: {type(e).__name__}]"


async def chat_stream(
    prompt: str,
    system: str = SYSTEM_TASADOR,
    session_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Pseudo-streaming: ejecuta sync y entrega chunks de ~80 chars al frontend."""
    if not _claude_available():
        yield "[Claude headless no disponible en este entorno.]"
        return
    try:
        model = await _get_active_model()
        full = await asyncio.to_thread(
            _run_claude_sync, prompt, system, model, 180
        )
        if not full:
            yield "[Tasador AI no devolvió respuesta]"
            return
        chunk = 80
        for i in range(0, len(full), chunk):
            yield full[i:i + chunk]
            await asyncio.sleep(0.02)
    except Exception as e:
        yield f"[Tasador AI error: {type(e).__name__}]"


async def analyze_property(property_data: dict) -> dict:
    """Análisis estructurado de una propiedad. Devuelve dict parseado del JSON.

    Repetimos el schema en el USER prompt porque los system prompts a veces los ignora
    el modelo si la entrada es larga o ambigua. Mejor doble seguro.
    """
    prompt = f"""Propiedad a analizar:
```json
{json.dumps(property_data, ensure_ascii=False, indent=2)}
```

Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE este schema flat (sin wrappers, sin keys extra):

```json
{{
  "summary": "una oración describiendo la propiedad y su segmento",
  "highlights": ["3-5 puntos fuertes concretos"],
  "concerns": ["2-3 riesgos o debilidades"],
  "suggested_condition": "uno de: a_estrenar, excelente, muy_bueno, bueno, regular, a_reciclar",
  "estimated_age_bracket": "uno de: 0-5, 5-15, 15-30, 30-50, 50+",
  "market_segment": "uno de: premium, alto, medio, estandar, economico",
  "ai_confidence": 0.85
}}
```

Las 7 keys son obligatorias. No agregues keys extra. No uses objetos anidados."""
    raw = await chat_complete(prompt, system=SYSTEM_ANALYZER)
    return _extract_json(raw)


def _extract_json(text: str) -> dict:
    """Extrae el primer bloque JSON de un texto. Tolerante a markdown fences."""
    if not text:
        return {}
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}
