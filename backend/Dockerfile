FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Chromium de Playwright para el scraping on-demand de portales con JS
# (ZonaProp/ML) -- ver backend/api/scraping.py::_fetch_html. El paquete
# `playwright` ya está en requirements.txt; esto baja el binario del browser
# + las libs de SO que necesita (--with-deps). Sin este paso, Playwright
# arranca pero `p.chromium.launch()` explota (falta el binario) y el
# servicio degrada en silencio a httpx sin JS -- insuficiente para esos
# portales (WO F3-04). Solo `chromium` (no firefox/webkit) para no pagar
# peso de imagen que no se usa. Ver backend/README.md por la estimación de
# peso y la decisión (no se pudo medir con un build real en este WO).
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --timeout 120
