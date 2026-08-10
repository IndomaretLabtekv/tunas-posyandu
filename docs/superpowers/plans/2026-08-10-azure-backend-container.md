# Azure Backend Container Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a lean production backend image that runs unchanged on Azure Container Apps.

**Architecture:** Keep one Python slim stage and preserve every current API route. Install only runtime dependencies, copy only runtime files, run Uvicorn as a non-root user, and use Docker's native health check against the existing OpenAPI endpoint.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Docker, Azure Container Apps.

---

### Task 1: Split Runtime Dependencies

**Files:**
- Create: `requirements-runtime.txt`

- [ ] Create the pinned runtime list with NumPy, pandas, scikit-learn, LightGBM, SHAP, joblib, headless OpenCV, Pillow, FastAPI, Uvicorn, multipart support, SQLAlchemy, psycopg2-binary, PyJWT, and pwdlib.

```txt
numpy==2.4.6
pandas==3.0.5
scikit-learn==1.9.0
lightgbm==4.7.0
shap==0.52.0
joblib==1.5.3
opencv-contrib-python-headless==5.0.0.93
pillow>=9.0
fastapi==0.115.6
uvicorn==0.34.0
python-multipart==0.0.20
sqlalchemy==2.0.51
psycopg2-binary==2.9.10
PyJWT==2.10.1
pwdlib[argon2]==0.2.1
```
- [ ] Exclude pytest, openpyxl, HTTPX, transformers, timm, einops, huggingface_hub, and kornia because they are test, training, or lazy optional model dependencies outside the active runtime path.
- [ ] Run `rtk git diff --check -- requirements-runtime.txt`.
- [ ] Commit only this file with `rtk git commit -m "chore(api): split runtime dependencies"`.

### Task 2: Harden the Production Image

**Files:**
- Modify: `api/Dockerfile`

- [ ] Replace the Dockerfile with one `python:3.12-slim` stage that sets `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, and `PORT=8000`.
- [ ] Install only `libgomp1` from apt for the LightGBM wheel, then install `requirements-runtime.txt` without a pip cache.
- [ ] Create UID/GID 10001, copy `api`, `cv`, `tabular`, `scripts`, `data/who/lhfa_lms.csv`, and `results/tabular/final/primary_model.joblib` with that ownership, then switch to the non-root user.
- [ ] Add `EXPOSE 8000`, a Python-standard-library health check for `http://127.0.0.1:${PORT}/openapi.json`, and this command:

```dockerfile
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

RUN groupadd --gid 10001 tunas && useradd --uid 10001 --gid 10001 --no-create-home tunas

COPY --chown=10001:10001 api ./api
COPY --chown=10001:10001 cv ./cv
COPY --chown=10001:10001 tabular ./tabular
COPY --chown=10001:10001 scripts ./scripts
COPY --chown=10001:10001 data/who/lhfa_lms.csv ./data/who/lhfa_lms.csv
COPY --chown=10001:10001 results/tabular/final/primary_model.joblib ./results/tabular/final/primary_model.joblib

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8000\")}/openapi.json', timeout=2)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
```

- [ ] Run `rtk git diff --check -- api/Dockerfile`.
- [ ] Commit only `api/Dockerfile` with `rtk git commit -m "build(api): harden production container"`.

### Task 3: Trim the Docker Context

**Files:**
- Modify: `.dockerignore`

- [ ] Ignore local environments, frontend assets, tests, docs, graph outputs, generated data, and experiment results.
- [ ] Re-include only `data/who/lhfa_lms.csv` and `results/tabular/final/primary_model.joblib` from ignored data trees.

```dockerignore
.git
.github
.venv
.omo
.superpowers
__pycache__
*.pyc
.pytest_cache
.mypy_cache
web
tests
docs
graphify-out
artifacts
data/*
!data/who/
data/who/*
!data/who/lhfa_lms.csv
results/*
!results/tabular/
results/tabular/*
!results/tabular/final/
results/tabular/final/*
!results/tabular/final/primary_model.joblib
```
- [ ] Run `rtk git diff --check -- .dockerignore`.
- [ ] Commit only `.dockerignore` with `rtk git commit -m "build(api): trim Docker context"`.

### Task 4: Container Verification

- [ ] Build with `rtk docker build --network host -f api/Dockerfile -t tunas-api:azure .`.
- [ ] Inspect the image and confirm user `10001:10001`, port `8000`, and the production command.
- [ ] Run the image against the existing PostgreSQL container with required JWT and database variables.
- [ ] Request `/openapi.json` and inspect Docker health.
- [ ] Do not commit generated files or unrelated worktree changes. Do not run the full test suite.
