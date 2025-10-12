from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import tensorflow as tf
from tensorflow import keras
import numpy as np
import cv2
from PIL import Image
import io
import os
from datetime import datetime
import uuid

# Import database components
from database import init_db, get_db, PredictionLog

# ========== Initialize FastAPI App ==========
app = FastAPI(
    title="OncoDetect API",
    description="AI-powered lung nodule malignancy detection with database logging",
    version="1.0.1"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Global Variables ==========
MODEL = None
MODEL_PATH = "oncodetect_model_v3.h5"
HEATMAP_DIR = "heatmaps"
IMG_SIZE = (224, 224)

os.makedirs(HEATMAP_DIR, exist_ok=True)

# ========== Startup: Load Model & Initialize DB ==========
@app.on_event("startup")
async def startup_event():
    global MODEL
    print("🚀 Starting OncoDetect API...")
    
    # Initialize database
    init_db()
    
    # Load model
    print("Loading model...")
    MODEL = keras.models.load_model(MODEL_PATH)
    print("✅ Model loaded successfully!")
    print("✅ Database initialized!")

# ========== Helper Functions ==========

def preprocess_image(image_bytes):
    """Preprocess uploaded image."""
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image = image.resize(IMG_SIZE)
    img_array = np.array(image).astype('uint8')
    img_array = np.expand_dims(img_array, axis=0)
    return img_array, image

def generate_simple_heatmap(image, prediction_score):
    """Generate visualization heatmap."""
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    y, x = np.ogrid[:h, :w]
    center_y, center_x = h // 2, w // 2
    mask = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    mask = 1 - (mask / mask.max())
    mask = mask * prediction_score
    heatmap = np.uint8(255 * mask)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    superimposed = cv2.addWeighted(img_bgr, 0.6, heatmap, 0.4, 0)
    return superimposed

# ========== API Endpoints ==========

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "OncoDetect API",
        "model_loaded": MODEL is not None,
        "version": "1.0.1",
        "database": "connected"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check with database stats."""
    prediction_count = db.query(PredictionLog).count()
    return {
        "status": "healthy",
        "model_loaded": MODEL is not None,
        "model_path": MODEL_PATH,
        "total_predictions": prediction_count,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Main prediction endpoint with database logging.
    """
    try:
        if MODEL is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and preprocess image
        image_bytes = await file.read()
        img_array, original_image = preprocess_image(image_bytes)
        
        # Make prediction
        prediction = MODEL.predict(img_array, verbose=0)[0][0]
        is_malignant = prediction > 0.5
        confidence = float(prediction if is_malignant else 1 - prediction)
        label = "Malignant" if is_malignant else "Benign"
        
        # Generate heatmap
        heatmap_image = generate_simple_heatmap(original_image, prediction)
        heatmap_filename = f"{uuid.uuid4()}.jpg"
        heatmap_path = os.path.join(HEATMAP_DIR, heatmap_filename)
        cv2.imwrite(heatmap_path, heatmap_image)
        
        # ========== Log to Database ==========
        db_log = PredictionLog(
            input_filename=file.filename,
            prediction_result=label,
            confidence_score=confidence,
            raw_score=float(prediction),
            heatmap_filename=heatmap_filename
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        
        # Prepare response
        response = {
            "prediction": label,
            "confidence": round(confidence * 100, 2),
            "raw_score": float(prediction),
            "heatmap_url": f"/heatmap/{heatmap_filename}",
            "timestamp": db_log.timestamp.isoformat(),
            "filename": file.filename,
            "prediction_id": db_log.id
        }
        
        print(f"✅ Prediction #{db_log.id}: {label} ({confidence*100:.1f}%) - {file.filename}")
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/heatmap/{filename}")
async def get_heatmap(filename: str):
    """Serve generated heatmap images."""
    file_path = os.path.join(HEATMAP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Heatmap not found")
    return FileResponse(file_path, media_type="image/jpeg")

@app.get("/predictions")
async def get_predictions(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent predictions from database."""
    predictions = db.query(PredictionLog).order_by(
        PredictionLog.timestamp.desc()
    ).limit(limit).all()
    
    return {
        "count": len(predictions),
        "predictions": [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "filename": p.input_filename,
                "prediction": p.prediction_result,
                "confidence": round(p.confidence_score * 100, 2)
            }
            for p in predictions
        ]
    }

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get prediction statistics."""
    total = db.query(PredictionLog).count()
    benign = db.query(PredictionLog).filter(
        PredictionLog.prediction_result == "Benign"
    ).count()
    malignant = db.query(PredictionLog).filter(
        PredictionLog.prediction_result == "Malignant"
    ).count()
    
    return {
        "total_predictions": total,
        "benign_count": benign,
        "malignant_count": malignant,
        "benign_percentage": round((benign / total * 100) if total > 0 else 0, 2),
        "malignant_percentage": round((malignant / total * 100) if total > 0 else 0, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
