FROM node:22-alpine AS ui
WORKDIR /ui
COPY deeptrace/frontend/package.json deeptrace/frontend/package-lock.json ./
RUN npm ci
COPY deeptrace/frontend ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FRONTEND_DIST=/app/frontend_dist \
    LIGHT_SEED=true \
    CORS_ORIGINS=*
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
COPY deeptrace/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY deeptrace/backend/app ./app
COPY --from=ui /ui/dist ./frontend_dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
