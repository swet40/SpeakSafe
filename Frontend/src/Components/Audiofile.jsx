import React, { useState, useEffect } from 'react';
import "./Dictaphone.css"; // Use the same CSS file for consistent styling
import { useSocket } from "../AppContext/SocketContext";

const Audiofile = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState('');
  const socket = useSocket();

  useEffect(() => {
    if (socket) {
      socket.on("prediction", (data) => {
        console.log("Received prediction:", data); 
        setPrediction(data);
      });

      return () => socket.off("prediction");
    }
  }, [socket]);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.type.startsWith('audio/')) {
        setSelectedFile(file);
        setError('');
        setTranscript('');
        setPrediction(null);
      } else {
        setError('Please select a valid audio file (mp3, wav, m4a, etc.)');
        setSelectedFile(null);
      }
    }
  };

  const handleUpload = async () => {
  if (!selectedFile) {
    setError('Please select an audio file first');
    return;
  }

  setIsUploading(true);
  setError('');
  setTranscript('Processing audio...');

  const formData = new FormData();
  formData.append('audio', selectedFile);

  try {
    // Call your Flask backend endpoint
    const response = await fetch('http://localhost:5000/api/upload-audio', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Upload failed');
    }

    const result = await response.json();
    console.log("Upload result:", result);
    
    const transcriptText = result.transcript || 'No transcript available';
    setTranscript(transcriptText);
    
    // Set fraud detection result directly from backend response
    if (result.fraud_detection) {
      setPrediction(result.fraud_detection);
    }

  } catch (err) {
    setError(err.message || 'Failed to process audio file. Please try again.');
    console.error('Upload error:', err);
    setTranscript('');
  } finally {
    setIsUploading(false);
  }
};

  const handleReset = () => {
    setSelectedFile(null);
    setTranscript('');
    setPrediction(null);
    setError('');
    const fileInput = document.getElementById('audioFileInput');
    if (fileInput) fileInput.value = '';
  };

  const getBackgroundColor = () => {
    const score = prediction?.fraud_probability;
    if (typeof score !== "number") return "bg-gray-100"; 
    if (score < 50) return "greenColor";
    if (score >= 50 && score < 75) return "orangeColor";
    return "redColor";
  };

  const getFileStatus = () => {
    if (isUploading) return "Processing...";
    if (selectedFile) return "File Selected";
    return "No File Selected";
  };

  return (
    <div className="dictaphone-container">
      <div className="dictaphone-card">
        <h2 className="dictaphone-title">🎙️ Speech Recognition</h2>
        
        {/* Status indicator matching the microphone status */}
        <span className={`microphone-status ${selectedFile ? "microphone-on" : "microphone-off"}`}>
          {getFileStatus()}
        </span>

        <button className="dictaphone-reset" onClick={handleReset}>
          Reset
        </button>

        {/* Hidden file input */}
        <input
          id="audioFileInput"
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {/* Single transcript area for uploaded audio */}
        <div className="dictaphone-transcript-total">
          {transcript || "Upload an audio file to see transcript..."}
        </div>

        {/* Fraud detection result - same styling as live detection */}
        {typeof prediction?.fraud_probability === "number" && (
          <div className={`dictaphone-transcript ${getBackgroundColor()}`}>
            <p><strong>Fraud Probability:</strong> <span className='predication-value'>{prediction.fraud_probability}%</span></p>
            <p><strong>Reason:</strong> {typeof prediction.reason === "string" && prediction.reason.trim() !== "" ? prediction.reason : "No reason provided"}</p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="dictaphone-transcript" style={{ backgroundColor: '#ff6b6b', color: 'white' }}>
            {error}
          </div>
        )}

        {/* File info display */}
        {selectedFile && (
          <div className="dictaphone-transcript" style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}>
            <p><strong>File:</strong> {selectedFile.name}</p>
            <p><strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        )}

        {/* Button container - same layout as microphone buttons */}
        <div className="button-container">
          <button 
            onClick={() => document.getElementById('audioFileInput').click()}
            className="microphone-button button-start"
            disabled={isUploading}
            style={{ 
              backgroundColor: selectedFile ? '#28a745' : '#007bff',
              borderColor: selectedFile ? '#28a745' : '#007bff'
            }}
          >
            <span style={{ fontSize: '18px' }}>
              {selectedFile ? '📁' : '📂'}
            </span>
          </button>

          <button 
            onClick={handleUpload}
            className="microphone-button button-stop"
            disabled={!selectedFile || isUploading}
            style={{ 
              opacity: (!selectedFile || isUploading) ? 0.5 : 1
            }}
          >
            <span style={{ fontSize: '18px' }}>
              {isUploading ? '⏳' : '🚀'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Audiofile;