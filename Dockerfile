# Build the website, then run API + site as one service.
FROM node:20.20.1-slim@sha256:450617c43da25e890a85e935526b3f6a8cfc5377155404a0074cb3116f48f06c AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12.13-slim@sha256:d657ab0ade19f404a6ccc883ab399540de667aff751748ce23c07330c5a89e64
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY core ./core
COPY etl ./etl
COPY ml ./ml
COPY models ./models
COPY data/processed ./data/processed
COPY --from=web /web/dist ./frontend/dist
RUN groupadd --system --gid 10001 scoutlens \
    && useradd --system --uid 10001 --gid scoutlens --create-home scoutlens
ENV PORT=7860 \
    ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '7860'), timeout=2).read()"]
USER scoutlens
# --forwarded-allow-ips="*": only the hosting platform's proxy can reach this port, and it sets the real client IP
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
