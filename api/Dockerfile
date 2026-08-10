FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

RUN groupadd --gid 10001 tunas \
    && useradd --uid 10001 --gid 10001 --no-create-home tunas

COPY --chown=10001:10001 api ./api
COPY --chown=10001:10001 cv ./cv
COPY --chown=10001:10001 tabular ./tabular
COPY --chown=10001:10001 scripts ./scripts
COPY --chown=10001:10001 data/who/lhfa_lms.csv ./data/who/lhfa_lms.csv
COPY --chown=10001:10001 results/tabular/final/primary_model.joblib ./results/tabular/final/primary_model.joblib

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/openapi.json' % os.getenv('PORT', '8000'), timeout=2)"]

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
