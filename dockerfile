# ─── Stage 1: build the Expo web frontend ─────────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Writes the static site to /static (the script's ../static)
RUN npm run build

# ─── Stage 2: Python API that also serves the built site ──────────────────────
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /static ./static

EXPOSE 8000

# Credentials and season come from the environment, e.g.
#   docker run --env-file .env -p 8000:8000 fantasy-prediction
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
