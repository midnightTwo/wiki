# ---- Stage 1: Build React Frontend ----
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python API Server ----
FROM python:3.12-slim

WORKDIR /app

# Install Docker CLI for Mailu integration
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://get.docker.com | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY webapp/ ./webapp/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create data dir
RUN mkdir -p /data

WORKDIR /app/webapp

ENV FLASK_APP=app.py
ENV MAIL_DOMAIN=komarnitsky.wiki
ENV DB_PATH=/data/komarnitsky-mail.db

EXPOSE 8000

CMD ["sh", "-c", "python -c 'from app import init_db; init_db()' && gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 app:app"]
