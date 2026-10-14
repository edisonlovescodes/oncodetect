"""Cropped lung-nodule image prototype; serving correctness is not clinical validation."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import io
import logging
import os
from pathlib import Path
from threading import Lock
import warnings

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session, sessionmaker

try:
    from .database import Base, PredictionLog, make_engine
except ImportError:  # also support `uvicorn main:app` from backend/
    from database import Base, PredictionLog, make_engine

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
IMG_SIZE = (224, 224)


def load_model(path):
    from tensorflow import keras  # model loading is optional for service tests

    return keras.models.load_model(path, compile=False)


def preprocess_image(data):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(413, "Image dimensions exceed the 16-million-pixel limit")
                if image.format not in {"PNG", "JPEG"}:
                    raise HTTPException(400, "Upload a PNG or JPEG nodule crop")
                image.load()
                # Preserve the packaged artifact's previous input contract; no recovered trainer
                # exists to establish its training-time normalization.
                rgb = image.convert("RGB").resize(IMG_SIZE)
                return np.expand_dims(np.asarray(rgb, dtype=np.uint8), 0)
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, "Image dimensions are too large") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Image could not be decoded") from None


def create_app(*, model_path=None, database_url=None, model_loader=load_model):
    artifact = Path(
        model_path or os.getenv("MODEL_PATH", ROOT / "oncodetect_model_v3.h5")
    ).resolve()
    data_dir = Path(os.getenv("ONCODETECT_DATA_DIR", ROOT / "data")).resolve()
    url = database_url or os.getenv("DATABASE_URL", f'sqlite:///{data_dir / "oncodetect.db"}')
    engine = make_engine(url)
    sessions = sessionmaker(bind=engine, autoflush=False)
    inference_lock = Lock()

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        app.state.model = None
        app.state.model_sha256 = None
        try:
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            app.state.model = model_loader(artifact)
            app.state.model_sha256 = digest
        except Exception:
            LOGGER.exception("Model unavailable; inference will return 503")
        try:
            yield
        finally:
            app.state.model = None
            engine.dispose()

    app = FastAPI(
        title="OncoDetect API",
        version="1.1.0",
        lifespan=lifespan,
        description="Research prototype for cropped nodule images; not whole-scan detection.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            s.strip()
            for s in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if s.strip()
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    routes = APIRouter()

    def get_db():
        with sessions() as session:
            yield session

    @routes.get("/")
    def root():
        return {"service": "OncoDetect API", "version": "1.1.0", "health_url": "/api/health"}

    @routes.get("/health")
    def health(db: Session = Depends(get_db)):
        ready = app.state.model is not None
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ready" if ready else "model_unavailable",
                "model_loaded": ready,
                "model_sha256": app.state.model_sha256,
                "total_predictions": db.query(PredictionLog).count(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluation_status": "historical accuracy not independently reproduced",
            },
        )

    @routes.post("/predict")
    def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
        if app.state.model is None:
            raise HTTPException(503, "Model unavailable")
        if file.content_type not in {"image/png", "image/jpeg"}:
            raise HTTPException(400, "Upload a PNG or JPEG nodule crop")
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Upload exceeds the 8 MiB limit")
        image = preprocess_image(data)
        try:
            # Sync route runs in FastAPI's thread pool. Serialize access to the model.
            with inference_lock:
                score = float(np.asarray(app.state.model.predict(image, verbose=0)).reshape(-1)[0])
            if not np.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid model score")
            label = "Malignant" if score > 0.5 else "Benign"
            class_score = score if score > 0.5 else 1 - score
            record = PredictionLog(
                input_filename=(file.filename or "upload")[:255],
                prediction_result=label,
                confidence_score=class_score,
                raw_score=score,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return {
                "prediction": label,
                "confidence": round(class_score * 100, 2),
                "raw_score": score,
                "timestamp": record.timestamp.replace(tzinfo=timezone.utc).isoformat(),
                "filename": record.input_filename,
                "prediction_id": record.id,
                "model_sha256": app.state.model_sha256,
                "score_note": "Model score, not a calibrated clinical probability",
            }
        except Exception:
            db.rollback()
            LOGGER.exception("Inference or persistence failed")
            raise HTTPException(500, "Prediction could not be completed") from None

    @routes.get("/predictions")
    def history(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
        records = (
            db.query(PredictionLog)
            .order_by(PredictionLog.timestamp.desc(), PredictionLog.id.desc())
            .limit(limit)
            .all()
        )
        return {
            "count": len(records),
            "predictions": [
                {
                    "id": p.id,
                    "timestamp": p.timestamp.replace(tzinfo=timezone.utc).isoformat(),
                    "filename": p.input_filename,
                    "prediction": p.prediction_result,
                    "confidence": round(p.confidence_score * 100, 2),
                }
                for p in records
            ],
        }

    @routes.get("/stats")
    def stats(db: Session = Depends(get_db)):
        total = db.query(PredictionLog).count()
        benign = db.query(PredictionLog).filter(PredictionLog.prediction_result == "Benign").count()
        malignant = total - benign
        return {
            "total_predictions": total,
            "benign_count": benign,
            "malignant_count": malignant,
            "benign_percentage": round(benign / total * 100, 2) if total else 0,
            "malignant_percentage": round(malignant / total * 100, 2) if total else 0,
        }

    app.include_router(routes, prefix="/api")
    # Preserve pre-refresh clients; both mounts share the same implementation.
    app.include_router(routes, include_in_schema=False)
    return app


app = create_app()
