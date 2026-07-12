FROM node:20-slim

WORKDIR /app

# Baileys instala deps transitivas desde git (libsignal de GitHub) -> el instalador
# necesita `git`, que no viene en node:20-slim. Sin esto, npm install corta con
# "npm error syscall spawn git / enoent". NO sacar.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Instala solo deps de produccion (usa el lockfile si esta presente).
COPY package*.json ./
RUN npm install --omit=dev

COPY src/ ./src/

# Cloud Run inyecta PORT; default 8080 para local/docker run.
ENV PORT=8080
EXPOSE 8080

CMD ["node", "src/index.js"]
