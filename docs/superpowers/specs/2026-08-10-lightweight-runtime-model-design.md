# Lightweight Runtime Model Design

## Goal

Make the backend container start without Debian package installation or runtime LightGBM, scikit-learn, SHAP, and joblib dependencies.

## Design

Training remains unchanged and still produces `primary_model.joblib`. A one-time exporter loads that trusted artifact and writes `primary_model.json` containing the LightGBM tree dump, ordered feature names, metadata, and normalized gain importance.

The API loads the JSON once and evaluates numeric tree splits in Python. Binary probabilities are the sigmoid of summed tree leaf values. Runtime explanation endpoints return precomputed global feature importance plus the current feature value; they no longer claim to provide per-child SHAP values.

## Runtime and Docker

The runtime requirements remove LightGBM, scikit-learn, SHAP, and joblib. The Dockerfile removes `apt-get` and `libgomp1`, copies the JSON artifact, and retains a BuildKit pip cache for subsequent builds. For the deadline machine, Compose reuses the already-built local image and current source bind mount instead of rebuilding.

## Verification

A parity test compares JSON evaluator probabilities with the original joblib model on fixed feature rows. API tests verify the global-importance response contract. Docker verification imports the remaining runtime packages and loads the JSON artifact without LightGBM or libgomp.
