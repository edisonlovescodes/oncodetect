# OncoDetect

A full-stack portfolio prototype for **cropped lung-nodule image classification**. A React interface submits PNG/JPEG crops to a FastAPI service, which runs a packaged TensorFlow ResNet50-based artifact and records results in SQLite. It does not locate nodules in whole CT volumes or diagnose patients.

## What is implemented

- Configurable, same-origin frontend/backend integration (`/api`), with explicit upload errors.
- Image decoding, file/pixel limits, bounded history queries, and persisted prediction counts.
- Model readiness and SHA-256 provenance; inference returns 503 when the artifact cannot load.
- Deterministic service tests, frontend workflow tests, and CI configuration.

The old center-weighted overlay has been removed: it was **not Grad-CAM or model attention**. Model scores are uncalibrated outputs, not clinical probabilities. Historical accuracy/recall claims are excluded because the original training data, split IDs and evaluation predictions are not tracked. Serving tests establish software behavior, not medical performance.

## Run locally

Python 3.12; Node 24. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci --ignore-scripts
npm start
```

Open http://localhost:3000. The Vite development proxy sends `/api` requests to port 8000. API documentation: http://127.0.0.1:8000/docs. Test with a public/synthetic PNG or JPEG crop; no patient uploads are needed. A constant image can demonstrate the request/history flow but is not a meaningful model evaluation.

`MODEL_PATH` defaults to the packaged backend artifact. `ONCODETECT_DATA_DIR` defaults to `backend/data/`; `DATABASE_URL` overrides SQLite. `CORS_ORIGINS` is a comma-separated allowlist for separately hosted clients. `VITE_API_BASE_URL` defaults to `/api`; a separate host must include the `/api` suffix. Set it at frontend build time. Old unprefixed API routes remain aliases, except the removed overlay endpoint.

Existing databases can still be opened by setting `DATABASE_URL`; they are not automatically copied from the old working directory. Old overlay filename columns remain readable. New predictions do not store images or generate overlays.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest tests -q
cd frontend
npm test
npm run build
```

Service tests use a deterministic fake model and temporary databases. TensorFlow is not required for those tests; an actual-artifact smoke run is a separate check. CI does not train or validate the medical model.

## Containers

```sh
docker compose up --build
```

The frontend nginx proxy retains `/api`, and a named volume persists the database. Readiness uses Python's standard library, not an absent curl executable. Ports bind to localhost. Container execution must be verified on a machine with Docker Compose; local tests do not prove container startup.

## Model and data limitations

The packaged artifact has a ResNet50 feature extractor and dense binary head. Its historical preprocessing/training provenance has not been recovered. Input conversion retains the previous uint8 RGB/224×224 serving contract rather than inventing a training normalization. Data-preparation scripts under `ml-model/` are historical research utilities, not a validated end-to-end training pipeline; the earlier unfinished v3 extractor is now retired. A trustworthy new evaluation needs patient-disjoint data, documented label semantics, split manifests, and saved predictions.

Source dataset: [TCIA LIDC-IDRI](https://www.cancerimagingarchive.net/collection/lidc-idri/). Nodule malignancy ratings are not equivalent to pathology-confirmed diagnoses.

See [CLAIMS.md](CLAIMS.md) for the current evidence boundary and [CHANGELOG.md](CHANGELOG.md) for this refresh.

## Interface and type

The interface uses self-hosted typefaces distributed by [Google Fonts](https://github.com/google/fonts). Original SIL Open Font License files are included in `frontend/public/fonts/`. No hosted font request is needed to render the page.
