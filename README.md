
# 🫁 OncoDetect - AI-Powered Lung Nodule Detection

A full-stack deep learning web application that analyzes lung CT scans to detect and classify nodules as benign or malignant, featuring real-time predictions, explainable AI visualizations, and comprehensive analytics.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.20-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![React](https://img.shields.io/badge/React-18-61dafb)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed)

---

## 🎯 Project Overview

OncoDetect leverages transfer learning with ResNet50 to provide automated lung nodule analysis. The system processes CT scan images and delivers instant predictions with confidence scores, helping support early cancer detection workflows.

### Key Metrics
- **Model Accuracy:** 85.71% on test set
- **Dataset:** 667 nodules from LIDC-IDRI (96 patients)
- **Benign Detection:** 97% recall
- **Architecture:** Full-stack containerized application

---

## 🏗️ System Architecture
┌─────────────────────────────────────────────────────────┐
│                  User Interface (React)                 │
│              Gradient UI • Real-time Updates            │
│                   localhost:3000                        │
└────────────────────┬────────────────────────────────────┘
│ HTTP/REST API
↓
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI + Python)             │
│    • Image Processing    • ML Inference                 │
│    • Heatmap Generation  • Database Logging             │
│                   localhost:8000                        │
└────────────────────┬────────────────────────────────────┘
│
┌────────────┴────────────┐
↓                         ↓
┌──────────────────┐    ┌──────────────────┐
│  ML Model        │    │  SQLite Database │
│  ResNet50        │    │  Prediction Logs │
│  85.71% Accuracy │    │  Analytics       │
└──────────────────┘    └──────────────────┘

---

## ✨ Features

### 🤖 Machine Learning
- **Transfer Learning** with pre-trained ResNet50
- **Binary Classification:** Benign vs. Malignant
- **Confidence Scores:** Percentage-based predictions
- **Medical Dataset:** Trained on LIDC-IDRI lung nodules

### 🎨 User Interface
- **Modern React Frontend** with gradient design
- **Drag & Drop Upload** with image preview
- **Real-time Predictions** with instant results
- **Attention Heatmaps** showing model focus areas
- **Responsive Design** for all screen sizes

### 📊 Analytics Dashboard
- **Prediction History** with timestamps
- **Statistics Overview:** Total predictions, distribution
- **Database Logging:** Complete audit trail
- **Performance Metrics:** Accuracy and confidence tracking

### 🐳 DevOps
- **Docker Containerization** for easy deployment
- **Multi-container Setup** (frontend + backend)
- **One-command Startup:** `docker compose up`
- **Production Ready** with Nginx reverse proxy

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- 8GB RAM minimum
- 10GB free disk space

### Run with Docker (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd oncodetect

# Start the application
docker compose up

# Open in browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
That's it! The entire application runs in Docker containers.

🛠️ Manual Setup (Development)
Backend Setup
bashcd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend server
python main.py
# Server starts at http://localhost:8000
Frontend Setup
bashcd frontend

# Install dependencies
npm install

# Start development server
npm start
# Opens browser at http://localhost:3000

📁 Project Structure
oncodetect/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── database.py             # Database models & config
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile             # Backend container config
│   ├── oncodetect_model_v3.h5 # Trained ML model
│   └── heatmaps/              # Generated visualizations
│
├── frontend/
│   ├── src/
│   │   ├── App.js             # Main React component
│   │   └── App.css            # Styling
│   ├── public/
│   ├── package.json           # Node dependencies
│   ├── Dockerfile             # Frontend container config
│   └── nginx.conf             # Nginx configuration
│
├── ml-model/
│   ├── preprocess_data_v3_fixed.py  # Data extraction
│   ├── processed_data_v3/           # Extracted nodules
│   └── raw_data/                    # LIDC-IDRI dataset
│
├── docker-compose.yml         # Multi-container orchestration
└── README.md                  # This file

🔬 Machine Learning Details
Model Architecture

Base Model: ResNet50 (pre-trained on ImageNet)
Transfer Learning: Frozen ResNet50 layers
Custom Head:

GlobalAveragePooling2D
Dense(128, activation='relu')
Dropout(0.5)
Dense(1, activation='sigmoid')



Training Details

Dataset: LIDC-IDRI (Lung Image Database Consortium)
Training Set: 533 nodules (80%)
Validation Set: 67 nodules (10%)
Test Set: 67 nodules (10%)
Optimizer: Adam (lr=0.001)
Loss Function: Binary Crossentropy
Epochs: 10

Performance Metrics
Test Accuracy: 85.71%

Classification Report:
              precision    recall  f1-score   support
      Benign       0.86      0.97      0.91        69
   Malignant       0.85      0.50      0.63        22
    accuracy                           0.86        91

🎯 API Endpoints
Core Endpoints
POST /predict
Upload an image for prediction
bashcurl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@nodule.png"
Response:
json{
  "prediction": "Benign",
  "confidence": 87.32,
  "raw_score": 0.1268,
  "heatmap_url": "/heatmap/abc-123.jpg",
  "timestamp": "2025-10-12T14:21:35.354133",
  "filename": "nodule.png",
  "prediction_id": 1
}
GET /predictions
Get recent prediction history
GET /stats
Get prediction statistics
GET /health
Health check with system info
Interactive API Documentation
Visit http://localhost:8000/docs for Swagger UI

📊 Database Schema
sqlCREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    input_filename VARCHAR,
    prediction_result VARCHAR,
    confidence_score FLOAT,
    raw_score FLOAT,
    heatmap_filename VARCHAR
);

🚀 Deployment
Docker Deployment
bash# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down

📈 Future Enhancements

 Multi-class classification (granular malignancy levels)
 3D volumetric analysis
 DICOM file support
 User authentication & multi-tenancy
 PostgreSQL for production database
 Advanced Grad-CAM visualizations


👨‍💻 Author
Edison Essien

Portfolio: edisoncodes.ai
LinkedIn: @essienedison
GitHub: edisonlovescodes
Email: organicedison@gmail.com


🙏 Acknowledgments

LIDC-IDRI Dataset: National Cancer Institute
ResNet50: Kaiming He et al.
FastAPI: Sebastián Ramírez
TensorFlow: Google Brain Team
React: Facebook/Meta


Built with ❤️ and lots of ☕
