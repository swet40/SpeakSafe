import React, { useState, useEffect } from 'react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { PiMicrophoneLight, PiMicrophoneSlash } from "react-icons/pi";
import SoundLoading from './SoundLoading';
import "./Dictaphone.css"
import { useSocket } from "../AppContext/SocketContext";

const Dictaphone = () => { 
  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();
  const [totalTranscript, setTotalTranscript] = useState();
  const [initialListening, setInitialListening] = useState(false);
  const [prediction, setPrediction] = useState();
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState('');
  const socket = useSocket();

  useEffect(() => {
    if (socket) {
      socket.on("prediction", (data) => {
        console.log("Received prediction:", data);
        console.log("Reason type:", typeof data.reason, "Value:", data.reason);
        setPrediction(data);
        
        // Check for API errors in the prediction
        if (data.api_error) {
          setApiError(data.reason);
        } else {
          setApiError('');
        }
      });

      socket.on("error", (data) => {
        console.log("Received error:", data);
        const errorMessage = data.error || "An error occurred";
        setError(errorMessage);
        setInitialListening(false);
        SpeechRecognition.stopListening();
      });

      return () => {
        socket.off("prediction");
        socket.off("error");
      };
    }
  }, [socket]);

  useEffect(() => {
    if (!initialListening)
      return;
    if (transcript && socket) {
      console.log(transcript);

      socket.emit("predict", { text: transcript, id: "user1" });

      setTotalTranscript((prev) => { 
        if (prev) return prev + transcript; 
        else return transcript 
      });
    }
    setTimeout(() => {
      if (initialListening && !error) {
        SpeechRecognition.startListening();
      }
    }, 500);
  }, [listening, socket, initialListening, error]);

  // Enhanced speech recognition error handling
  const handleSpeechRecognitionError = (error) => {
    console.error('Speech recognition error:', error);
    
    if (typeof error === 'string') {
      // Handle different types of speech recognition errors
      if (error.includes('network') || error.includes('no-speech')) {
        setError('🌐 Network error or no speech detected. Please check your connection and try speaking clearly.');
      } else if (error.includes('audio-capture') || error.includes('not-allowed')) {
        setError('🎤 Microphone permission denied. Please allow microphone access and try again.');
      } else if (error.includes('service-not-allowed') || error.includes('not-supported')) {
        setError('🎤 Speech recognition not supported in this browser. Please use Chrome or Edge.');
      } else if (error.includes('aborted')) {
        setError('🎤 Speech recognition was stopped. You can start again.');
      } else {
        setError('❌ Speech recognition error. Please try again.');
      }
    } else {
      setError('❌ Speech recognition error. Please try again.');
    }
    
    setInitialListening(false);
  };

  // Check browser support with better error message
  if (!browserSupportsSpeechRecognition) {
    return (
      <div className="dictaphone-container">
        <div className="dictaphone-card">
          <div className="dictaphone-transcript" style={{ 
            backgroundColor: '#f44336', 
            color: 'white',
            textAlign: 'center',
            padding: '20px'
          }}>
            🎤 Speech recognition not supported in this browser. 
            <br />Please use Chrome, Edge, or Safari for the best experience.
          </div>
        </div>
      </div>
    );
  }
  
  const getBackgroundColor = () => {
    const score = prediction?.fraud_probability;
    if (typeof score !== "number") return "bg-gray-100"; 
    if (score < 50) return "greenColor";
    if (score >= 50 && score < 75) return "orangeColor";
    return "redColor";
  };

  // Error display component
  const ErrorDisplay = ({ error, type = "general" }) => {
    if (!error) return null;
    
    const getErrorStyle = () => {
      if (type === "api" || error.includes('GEMINI_') || error.includes('⚠️')) {
        return { 
          backgroundColor: '#ff9800', 
          color: 'white',
          border: '2px solid #f57c00'
        };
      } else if (error.includes('🔊') || error.includes('🎤')) {
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

  // Enhanced start listening function
  const startListening = () => {
    // Clear any existing errors
    setError('');
    setApiError('');
    
    try {
      SpeechRecognition.startListening({ 
        continuous: true,
        language: 'en-US'
      });
      setInitialListening(true);
    } catch (err) {
      console.error('Error starting speech recognition:', err);
      handleSpeechRecognitionError('Failed to start speech recognition');
    }
  };

  // Enhanced stop listening function
  const stopListening = () => {
    try {
      SpeechRecognition.stopListening();
      setInitialListening(false);
    } catch (err) {
      console.error('Error stopping speech recognition:', err);
    }
  };

  // Enhanced reset function
  const resetAll = () => {
    resetTranscript();
    setTotalTranscript("");
    setPrediction();
    setError('');
    setApiError('');
    setInitialListening(false);
    SpeechRecognition.stopListening();
  };

  // Check if microphone is working
  const checkMicrophonePermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (err) {
      setError('🎤 Microphone permission denied. Please allow microphone access in your browser settings.');
      return false;
    }
  };

  // Enhanced start with permission check
  const startWithPermissionCheck = async () => {
    const hasPermission = await checkMicrophonePermission();
    if (hasPermission) {
      startListening();
    }
  };

  return (
    <div className="dictaphone-container">
      <div className="dictaphone-card">
        <h2 className="dictaphone-title">🎙️ Speech Recognition</h2>
        
        <span className={`microphone-status ${listening ? "microphone-on" : "microphone-off"}`}>
          {listening ? "Listening..." : "Microphone Off"}
        </span>

        <button className="dictaphone-reset" onClick={resetAll}>
          Reset
        </button>

        <div className="dictaphone-transcript">
          {transcript || "Start speaking..."}
        </div>
        
        <div className="dictaphone-transcript-total">
          {totalTranscript || "Total transcript will appear here..."}
        </div>

        {/* General error display */}
        <ErrorDisplay error={error} type="general" />

        {/* API error display (for Gemini quota issues) */}
        <ErrorDisplay error={apiError} type="api" />

        {/* Fraud detection result */}
        {typeof prediction?.fraud_probability === "number" && (
          <div className={`dictaphone-transcript ${getBackgroundColor()}`}>
            <p><strong>Fraud Probability:</strong> <span className='predication-value'>{prediction.fraud_probability}%</span></p>
            <p><strong>Reason:</strong> {typeof prediction.reason === "string" && prediction.reason.trim() !== "" ? prediction.reason : "No reason provided"}</p>
          </div>
        )}

        {listening && <SoundLoading />}

        <div className="button-container">
          <button 
            onClick={startWithPermissionCheck}
            className="microphone-button button-start"
            disabled={listening || !!error}
          >
            <PiMicrophoneLight size={30} />
          </button>

          <button 
            onClick={stopListening}
            className="microphone-button button-stop"
            disabled={!listening}
          >
            <PiMicrophoneSlash size={30} />
          </button>
        </div>

        {/* Status indicators */}
        {error && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <button 
              onClick={() => setError('')}
              style={{
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Clear Error & Try Again
            </button>
          </div>
        )}

        {apiError && (
          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <small style={{ color: '#ff9800', fontWeight: 'bold' }}>
              ⚠️ AI analysis temporarily limited, but fraud detection is still working
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dictaphone;