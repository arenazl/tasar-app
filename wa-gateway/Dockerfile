FROM node:20-slim

WORKDIR /app

# Baileys trae deps transitivas desde git (libsignal, eslint-config, etc.) -> se
# necesita `git` (no viene en node:20-slim). Ademas algunas usan URLs git+ssh
# (ssh://git@github.com/...) que en un build sin ssh-key fallan con "ssh: not found":
# las reescribimos a HTTPS (repos publicos, sin credenciales). NO sacar ninguna de las dos.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" \
    && git config --global url."https://github.com/".insteadOf "git@github.com:"

# Instala solo deps de produccion (usa el lockfile si esta presente).
COPY package*.json ./
RUN npm install --omit=dev

COPY src/ ./src/

# Cloud Run inyecta PORT; default 8080 para local/docker run.
ENV PORT=8080
EXPOSE 8080

CMD ["node", "src/index.js"]
