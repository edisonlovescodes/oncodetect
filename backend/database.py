"""Prediction storage. Existing databases remain readable; no schema migration required."""

from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def make_engine(url):
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        if parsed.database and parsed.database != ":memory:":
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


class PredictionLog(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    input_filename = Column(String, nullable=False)
    prediction_result = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    raw_score = Column(Float, nullable=False)
    # Kept for compatibility with existing data. New predictions do not create an overlay.
    heatmap_filename = Column(String, nullable=True)
