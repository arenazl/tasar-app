FROM node:20-slim

WORKDIR /app

# Instala solo deps de produccion (usa el lockfile si esta presente).
COPY package*.json ./
RUN npm install --omit=dev

COPY src/ ./src/

# Cloud Run inyecta PORT; default 8080 para local/docker run.
ENV PORT=8080
EXPOSE 8080

CMD ["node", "src/index.js"]
