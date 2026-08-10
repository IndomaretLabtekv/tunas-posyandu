# Lightweight Runtime Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace runtime joblib/LightGBM/SHAP inference with a JSON tree evaluator and remove apt from the backend image.

**Architecture:** Keep training dependencies and reports unchanged. Export the trusted training artifact once, then load and evaluate its numeric tree dump using the API's existing NumPy/pandas runtime.

**Tech Stack:** Python 3.12, JSON, NumPy, pandas, FastAPI, Docker BuildKit.

## Global Constraints

- Preserve prediction probability within `1e-12` of LightGBM on the parity fixture.
- Explanations are global gain importance, not per-child SHAP.
- Runtime Docker build must contain no `apt-get`, LightGBM, scikit-learn, SHAP, or joblib.

---

### Task 1: JSON evaluator and exporter

**Files:**
- Create: `scripts/export_runtime_model.py`
- Modify: `api/model.py`
- Test: `tests/test_runtime_model.py`

**Interfaces:**
- Produces: `predict_scores(frame: pd.DataFrame) -> np.ndarray` and `explain_row(frame, row_index, top_k) -> list[dict]` from a version-2 JSON artifact.

- [ ] Write a failing test that loads a small JSON tree artifact and checks split, missing-value, sigmoid, and global-importance behavior.
- [ ] Run `pytest tests/test_runtime_model.py -q` and confirm failure because the JSON loader is absent.
- [ ] Implement the minimal cached JSON loader and iterative numeric-tree evaluator.
- [ ] Add the exporter using `model.booster_.dump_model()` and normalized gain importance.
- [ ] Export `results/tabular/final/primary_model.json` from the trusted joblib artifact.
- [ ] Add and run a parity test against the joblib model with tolerance `1e-12`.
- [ ] Commit evaluator, exporter, artifact, and tests.

### Task 2: API explanation contract

**Files:**
- Modify: `api/schemas.py`
- Modify: `api/routes.py`
- Modify: `tests/test_api_priority.py`

**Interfaces:**
- Produces: top factors with `feature`, `label`, `value`, and normalized `importance`.

- [ ] Change the API test to require the global-importance fields and disclaimer wording.
- [ ] Run the focused API test and confirm it fails on the SHAP contract.
- [ ] Update schemas and copy to global importance without causal or local-attribution claims.
- [ ] Run focused model and API tests.
- [ ] Commit the API contract change.

### Task 3: Lightweight Docker runtime

**Files:**
- Modify: `requirements-runtime.txt`
- Modify: `api/Dockerfile`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `results/tabular/final/primary_model.json`.
- Produces: backend image with no Debian package install or training-only ML stack.

- [ ] Remove training-only packages from runtime requirements and switch model paths to JSON.
- [ ] Remove apt/libgomp from Dockerfile and copy the JSON artifact.
- [ ] Run static checks proving banned packages and `apt-get` are absent.
- [ ] Reuse the existing local backend image for immediate no-build startup; build the lightweight image once Docker outbound networking is restored.
- [ ] Commit Docker/runtime changes.
