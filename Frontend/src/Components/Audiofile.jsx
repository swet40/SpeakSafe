import React, { useState, useEffect } from 'react';
import "./Dictaphone.css"; // Use the same CSS file for consistent styling
import { useSocket } from "../AppContext/SocketContext";

const Audiofile = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState('');
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
      // Enhanced file validation
      const maxSize = 50 * 1024 * 1024; // 50MB limit
      const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/m4a', 'audio/webm', 'audio/ogg'];
      
      if (!file.type.startsWith('audio/') && !allowedTypes.some(type => file.type === type)) {
        setError('🎵 Please select a valid audio file (mp3, wav, m4a, etc.)');
        setSelectedFile(null);
        return;
      }
      
      if (file.size > maxSize) {
        setError('📁 File size too large. Please select a file smaller than 50MB.');
        setSelectedFile(null);
        return;
      }
      
      if (file.size === 0) {
        setError('📁 Selected file is empty. Please choose a different file.');
        setSelectedFile(null);
        return;
      }

      setSelectedFile(file);
      setError('');
      setApiError('');
      setTranscript('');
      setPrediction(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select an audio file first');
      return;
    }

    setIsUploading(true);
    setError('');
    setApiError('');
    setTranscript('Processing audio...');
    setPrediction(null);

    const formData = new FormData();
    formData.append('audio', selectedFile);

    try {
      // Call your Flask backend endpoint
      const response = await fetch('http://localhost:5000/api/upload-audio', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        // Handle different types of errors from backend
        const errorMessage = result.error || 'Upload failed';
        
        // Check for API quota/limit errors
        if (errorMessage.includes('quota') || errorMessage.includes('limit')) {
          setApiError(errorMessage);
        } else if (errorMessage.includes('🔊') || errorMessage.includes('transcription')) {
          setError(errorMessage);
        } else if (errorMessage.includes('authentication') || errorMessage.includes('API key')) {
          setApiError('🔑 Service authentication error. Please contact support.');
        } else {
          setError(errorMessage);
        }
        
        setTranscript('');
        return;
      }

      console.log("Upload result:", result);
      
      const transcriptText = result.transcript || 'No transcript available';
      setTranscript(transcriptText);
      
      // Set fraud detection result directly from backend response
      if (result.fraud_detection) {
        setPrediction(result.fraud_detection);
        
        // Check for API errors in fraud detection
        if (result.fraud_detection.api_error) {
          setApiError(result.fraud_detection.reason);
        }
      }

    } catch (err) {
      console.error('Upload error:', err);
      
      // Handle network errors
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('🌐 Unable to connect to server. Please check your internet connection.');
      } else if (err.message.includes('timeout')) {
        setError('⏱️ Request timed out. Please try again with a smaller file.');
      } else if (err.message.includes('NetworkError')) {
        setError('🌐 Network error. Please check your connection and try again.');
      } else {
        setError('❌ Something went wrong. Please try again.');
      }
      
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
    setApiError('');
    setIsUploading(false);
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

  // Error display component
  const ErrorDisplay = ({ error, type = "general" }) => {
    if (!error) return null;
    
    const getErrorStyle = () => {
      if (type === "api" || error.includes('quota') || error.includes('limit') || error.includes('⚠️')) {
        return { 
          backgroundColor: '#ff9800', 
          color: 'white',
          border: '2px solid #f57c00'
        };
      } else if (error.includes('🔊') || error.includes('🎵') || error.includes('📁')) {
        return { 
          backgroundColor: '#2196f3', 
          color: 'white',
          border: '2px solid #1976d2'
        };
      } else {
        return { 
          backgroundColor: '#f44336', 
          color: 'white',
          border: '2px solid #d32f2f'
        };
      }
    };

    return (
      <div 
        className="dictaphone-transcript" 
        style={{
          ...getErrorStyle(),
          fontWeight: 'bold',
          textAlign: 'center',
          padding: '15px',
          borderRadius: '8px',
          margin: '10px 0'
        }}
      >
        {error}
      </div>
    );
  };

  // File validation helper
  const validateFile = (file) => {
    if (!file) return false;
    
    const maxSize = 50 * 1024 * 1024; // 50MB
    const minSize = 1024; // 1KB minimum
    
    return file.size >= minSize && file.size <= maxSize && file.type.startsWith('audio/');
  };

  // Retry function for quota errors
  const handleRetry = () => {
    setError('');
    setApiError('');
    if (selectedFile) {
      handleUpload();
    }
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

        {/* General error display */}
        <ErrorDisplay error={error} type="general" />

        {/* API error display (for Gemini/Deepgram quota issues) */}
        <ErrorDisplay error={apiError} type="api" />

        {/* Fraud detection result - same styling as live detection */}
        {typeof prediction?.fraud_probability === "number" && (
          <div className={`dictaphone-transcript ${getBackgroundColor()}`}>
            <p><strong>Fraud Probability:</strong> <span className='predication-value'>{prediction.fraud_probability}%</span></p>
            <p><strong>Reason:</strong> {typeof prediction.reason === "string" && prediction.reason.trim() !== "" ? prediction.reason : "No reason provided"}</p>
          </div>
        )}

        {/* File info display */}
        {selectedFile && (
          <div className="dictaphone-transcript" style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}>
            <p><strong>File:</strong> {selectedFile.name}</p>
            <p><strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            <p><strong>Type:</strong> {selectedFile.type}</p>
          </div>
        )}

        {/* Button container - same layout as microphone buttons */}
        <div className="button-container">
          <button 
            onClick={() => document.getElementById('audioFileInput').click()}
            className="microphone-button button-start"
            disabled={isUploading}
            style={{ 
              backgroundColor: selectedFile ? '#00d4aa' : '#4a90e2',
              borderColor: selectedFile ? '#00d4aa' : '#4a90e2',
              opacity: isUploading ? 0.5 : 1,
              color: 'white',
              boxShadow: selectedFile ? '0 4px 15px rgba(0, 212, 170, 0.3)' : '0 4px 15px rgba(74, 144, 226, 0.3)'
            }}
          >
            <span style={{ fontSize: '18px' }}>
              {selectedFile ? '📁' : '📂'}
            </span>
          </button>

          <button 
            onClick={handleUpload}
            className="microphone-button button-stop"
            disabled={!selectedFile || isUploading || !validateFile(selectedFile)}
            style={{ 
              backgroundColor: (!selectedFile || isUploading || !validateFile(selectedFile)) ? '#6c757d' : '#ff6b35',
              borderColor: (!selectedFile || isUploading || !validateFile(selectedFile)) ? '#6c757d' : '#ff6b35',
              opacity: (!selectedFile || isUploading || !validateFile(selectedFile)) ? 0.5 : 1,
              color: 'white',
              boxShadow: (!selectedFile || isUploading || !validateFile(selectedFile)) ? 'none' : '0 4px 15px rgba(255, 107, 53, 0.3)'
            }}
          >
            <span style={{ fontSize: '18px' }}>
              {isUploading ? '⏳' : '🚀'}
            </span>
          </button>
        </div>

        {/* Status indicators and action buttons */}
        {error && !apiError && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <button 
              onClick={() => setError('')}
              style={{
                backgroundColor: '#00d4aa',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                marginRight: '10px',
                boxShadow: '0 2px 8px rgba(0, 212, 170, 0.3)',
                fontSize: '14px'
              }}
            >
              Clear Error
            </button>
            {selectedFile && (
              <button 
                onClick={handleRetry}
                style={{
                  backgroundColor: '#4a90e2',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(74, 144, 226, 0.3)',
                  fontSize: '14px'
                }}
              >
                Try Again
              </button>
            )}
          </div>
        )}

        {apiError && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <small style={{ color: '#ffa726', fontWeight: 'bold', display: 'block', marginBottom: '10px' }}>
              ⚠️ Service temporarily limited, but basic fraud detection still works
            </small>
            <button 
              onClick={handleRetry}
              style={{
                backgroundColor: '#2f2695',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(255, 167, 38, 0.3)',
                fontSize: '14px'
              }}
            >
              🔄 Try Again Later
            </button>
          </div>
        )}

        {/* Upload progress indicator */}
        {isUploading && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <small style={{ color: '#4a90e2', fontWeight: 'bold' }}>
              📤 Processing your audio file... Please wait.
            </small>
          </div>
        )}

        {/* File requirements info */}
        {!selectedFile && !error && !apiError && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <small style={{ color: '#8a9ba8', fontSize: '12px' }}>
              Supported: MP3, WAV, M4A • Max size: 50MB
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

export default Audiofile;