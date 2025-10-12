import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'https://oncodetect-backend-edison.onrender.com';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);

  // Load history and stats on mount
  useEffect(() => {
    fetchHistory();
    fetchStats();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/predictions?limit=5`);
      setHistory(response.data.predictions);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select an image first');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API_BASE_URL}/predict`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(response.data);
      fetchHistory();
      fetchStats();
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error making prediction. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🫁 OncoDetect</h1>
        <p className="subtitle">AI-Powered Lung Nodule Analysis</p>
      </header>

      <div className="container">
        {/* Upload Section */}
        <div className="card upload-section">
          <h2>Upload CT Scan</h2>
          
          <div className="upload-area">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              id="file-input"
              style={{ display: 'none' }}
            />
            <label htmlFor="file-input" className="upload-button">
              Choose Image
            </label>
            
            {preview && (
              <div className="preview-container">
                <img src={preview} alt="Preview" className="preview-image" />
                <p className="filename">{selectedFile.name}</p>
              </div>
            )}
          </div>

          <div className="button-group">
            <button
              onClick={handleUpload}
              disabled={!selectedFile || loading}
              className="btn btn-primary"
            >
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
            <button
              onClick={handleReset}
              disabled={!selectedFile}
              className="btn btn-secondary"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="card results-section">
            <h2>Analysis Results</h2>
            
            <div className="result-grid">
              <div className="result-item">
                <div className={`prediction-badge ${result.prediction.toLowerCase()}`}>
                  {result.prediction}
                </div>
                <div className="confidence">
                  Confidence: {result.confidence}%
                </div>
              </div>

              {result.heatmap_url && (
                <div className="heatmap-container">
                  <h3>Attention Heatmap</h3>
                  <img
                    src={`${API_BASE_URL}${result.heatmap_url}`}
                    alt="Heatmap"
                    className="heatmap-image"
                  />
                </div>
              )}
            </div>

            <div className="result-details">
              <p><strong>Prediction ID:</strong> {result.prediction_id}</p>
              <p><strong>Timestamp:</strong> {new Date(result.timestamp).toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Stats Section */}
        {stats && (
          <div className="card stats-section">
            <h2>Statistics</h2>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{stats.total_predictions}</div>
                <div className="stat-label">Total Predictions</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{stats.benign_count}</div>
                <div className="stat-label">Benign</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{stats.malignant_count}</div>
                <div className="stat-label">Malignant</div>
              </div>
            </div>
          </div>
        )}

        {/* History Section */}
        {history.length > 0 && (
          <div className="card history-section">
            <h2>Recent Predictions</h2>
            <div className="history-list">
              {history.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-info">
                    <span className="history-filename">{item.filename}</span>
                    <span className="history-time">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="history-result">
                    <span className={`badge ${item.prediction.toLowerCase()}`}>
                      {item.prediction}
                    </span>
                    <span className="history-confidence">
                      {item.confidence}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <footer className="App-footer">
        <p>OncoDetect v1.0 | AI-Powered Medical Imaging Analysis</p>
      </footer>
    </div>
  );
}

export default App;
