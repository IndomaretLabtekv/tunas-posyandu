# Azure Backend Container Design

## Goal

Make the existing FastAPI backend container small, production-safe, and compatible with Azure Container Apps without changing API behavior.

## Minimal Design

Use one `python:3.12-slim` stage. Remove `apt-get`, `gcc`, and `libpq-dev` because runtime uses binary wheels. Install a dedicated `requirements-runtime.txt` containing only packages required by current API, CV, model loading, and explanation routes. Use headless OpenCV to avoid GUI libraries.

Copy only runtime source, the WHO table, the model artifact, and the demo seed module. Run Uvicorn as a non-root user on `${PORT:-8000}` with one worker by default. Add a Docker-native health check against FastAPI's existing OpenAPI endpoint, avoiding new application code solely for the platform.

Trim Docker build context while retaining `data/who/lhfa_lms.csv` and `results/tabular/final/primary_model.joblib`.

## Explicitly Excluded

- Azure infrastructure-as-code and deployment scripts
- frontend container changes
- API, authentication, CORS, database, or workflow behavior changes
- multi-stage wheel builds and custom entrypoint scripts
- training, experiment, notebook, and test dependencies

## Commits

1. Split backend runtime dependencies.
2. Harden the production backend image.
3. Trim Docker build context.

Each commit contains only its named concern. Existing unrelated worktree changes remain unstaged.

## Verification

Build the backend image, inspect its configured user and command, start it against the existing local PostgreSQL service, and request `/openapi.json`. Do not run the full automated test suite in this pass.
