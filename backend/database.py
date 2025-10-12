from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL - using SQLite for development (easier setup)
# For production, you'd use: postgresql://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./oncodetect.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== Prediction Log Model ==========
class PredictionLog(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    input_filename = Column(String, nullable=False)
    prediction_result = Column(String, nullable=False)  # "Benign" or "Malignant"
    confidence_score = Column(Float, nullable=False)
    raw_score = Column(Float, nullable=False)
    heatmap_filename = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, result={self.prediction_result}, confidence={self.confidence_score})>"

# ========== Initialize Database ==========
def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
