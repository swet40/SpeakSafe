from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import joblib
import os
import json
import tempfile
from genai import gen_ai_json
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException, HTTPError, Timeout

load_dotenv()

app = Flask(__name__)
cors_origin = os.getenv("CORS_ALLOWED_ORIGIN", "*")
socketio = SocketIO(app, cors_allowed_origins=cors_origin)
CORS(app)

base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, 'model', 'model2.pkl')
vectorizer_path = os.path.join(base_dir, 'model', 'vectorizer2.pkl')
model = joblib.load(model_path)
vectorizer = joblib.load(vectorizer_path)

store = {}

def handle_deepgram_response(response):
    """Handle Deepgram API response and raise appropriate errors"""
    if response.status_code == 401:
        raise ValueError("DEEPGRAM_AUTH_ERROR: Invalid or missing Deepgram API key")
    elif response.status_code == 402:
        raise ValueError("DEEPGRAM_QUOTA_EXCEEDED: Deepgram free tier limit exceeded. Please upgrade your plan or wait for quota reset.")
    elif response.status_code == 429:
        raise ValueError("DEEPGRAM_RATE_LIMIT: Too many requests to Deepgram API. Please try again later.")
    elif response.status_code == 400:
        try:
            error_detail = response.json().get('err_msg', 'Invalid request')
        except:
            error_detail = 'Invalid audio format or request'
        raise ValueError(f"DEEPGRAM_BAD_REQUEST: {error_detail}")
    elif response.status_code >= 500:
        raise ValueError("DEEPGRAM_SERVER_ERROR: Deepgram service is temporarily unavailable. Please try again later.")
    
    response.raise_for_status()

def extract_transcript_from_response(result):
    """Extract transcript from Deepgram response"""
    if (result
        and "results" in result 
        and "channels" in result["results"]
        and len(result["results"]["channels"]) > 0
        and "alternatives" in result["results"]["channels"][0]
        and len(result["results"]["channels"][0]["alternatives"]) > 0
        and "transcript" in result["results"]["channels"][0]["alternatives"][0]):
        
        transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        if transcript and transcript.strip():
            return transcript
        else:
            raise ValueError("DEEPGRAM_NO_SPEECH: No speech detected in the audio")
    else:
        raise ValueError("DEEPGRAM_INVALID_RESPONSE: Invalid response structure from Deepgram API")

def transcribe_audio(audio_file, mimetype, language="en"):
    """Transcribe audio using Deepgram API with enhanced error handling"""
    url = f"https://api.deepgram.com/v1/listen?language={language}"
    headers = {
        "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
        "Content-Type": mimetype,
    }
    
    try:
        response = requests.post(url, data=audio_file.read(), headers=headers, timeout=30)
        handle_deepgram_response(response)
        result = response.json()
        return extract_transcript_from_response(result)
        
    except Timeout:
        raise ValueError("DEEPGRAM_TIMEOUT: Request to Deepgram API timed out. Please try again.")
    except RequestException as e:
        raise ValueError("DEEPGRAM_CONNECTION_ERROR: Unable to connect to Deepgram API. Please check your internet connection.")
    except Exception as e:
        if "DEEPGRAM_" in str(e):
            raise e
        print(f"Unexpected Deepgram error: {str(e)}")
        raise ValueError("DEEPGRAM_UNKNOWN_ERROR: An unexpected error occurred during transcription")

def transcribe_audio_file(file_path, mimetype, language="en"):
    """Transcribe audio file from file path using Deepgram API with enhanced error handling"""
    url = f"https://api.deepgram.com/v1/listen?language={language}"
    headers = {
        "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
        "Content-Type": mimetype,
    }
    
    try:
        with open(file_path, 'rb') as audio_file:
            response = requests.post(url, data=audio_file, headers=headers, timeout=30)
        handle_deepgram_response(response)
        result = response.json()
        return extract_transcript_from_response(result)
        
    except Timeout:
        raise ValueError("DEEPGRAM_TIMEOUT: Request to Deepgram API timed out. Please try again.")
    except RequestException as e:
        raise ValueError("DEEPGRAM_CONNECTION_ERROR: Unable to connect to Deepgram API. Please check your internet connection.")
    except Exception as e:
        if "DEEPGRAM_" in str(e):
            raise e
        print(f"Unexpected Deepgram error: {str(e)}")
        raise ValueError("DEEPGRAM_UNKNOWN_ERROR: An unexpected error occurred during transcription")

def get_fraud_result(text, score):
    """Generate fraud detection result with reason if score >= 75 and enhanced Gemini error handling"""
    THRESHOLD = 75

    if score >= THRESHOLD:
        try:
            result = gen_ai_json(text)

            # If result is a string, attempt to parse it
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    # If string is not JSON, fallback to empty dict
                    result = {}

            # Ensure result is a dictionary
            if not isinstance(result, dict):
                raise ValueError("Result is not a dictionary")

            # Always set fraud probability from backend
            result["fraud_probability"] = score

            # Ensure reason exists
            result["reason"] = result.get("reason", "No reason provided by AI")

        except Exception as e:
            error_message = str(e).lower()
            
            # Check for specific Gemini API errors
            if any(keyword in error_message for keyword in ["quota", "limit", "exceeded", "resource_exhausted"]):
                result = {
                    "fraud_probability": score,
                    "reason": "⚠️ GEMINI_QUOTA_EXCEEDED: AI analysis quota exceeded. Fraud detected based on ML model only.",
                    "api_error": True
                }
            elif any(keyword in error_message for keyword in ["api key", "authentication", "unauthorized", "invalid_argument"]):
                result = {
                    "fraud_probability": score,
                    "reason": "⚠️ GEMINI_AUTH_ERROR: AI analysis authentication error. Fraud detected based on ML model only.",
                    "api_error": True
                }
            elif any(keyword in error_message for keyword in ["rate limit", "too many requests"]):
                result = {
                    "fraud_probability": score,
                    "reason": "⚠️ GEMINI_RATE_LIMIT: AI analysis rate limit exceeded. Fraud detected based on ML model only.",
                    "api_error": True
                }
            else:
                print("Error parsing AI response:", e)
                result = {
                    "fraud_probability": score,
                    "reason": "⚠️ GEMINI_ERROR: AI analysis temporarily unavailable. Fraud detected based on ML model only.",
                    "api_error": True
                }

        return result

    return {
        "fraud_probability": score,
        "reason": ""
    }

def get_user_friendly_error(error_message):
    """Convert technical errors to user-friendly messages"""
    error_message = str(error_message)
    
    if "DEEPGRAM_QUOTA_EXCEEDED" in error_message:
        return "🔊 Audio transcription quota exceeded. Please try again later or contact support to upgrade your plan."
    elif "DEEPGRAM_RATE_LIMIT" in error_message:
        return "🔊 Too many audio requests. Please wait a moment and try again."
    elif "DEEPGRAM_AUTH_ERROR" in error_message:
        return "🔊 Audio transcription service authentication error. Please contact support."
    elif "DEEPGRAM_NO_SPEECH" in error_message:
        return "🔊 No speech detected in the audio. Please speak clearly or check your microphone."
    elif "DEEPGRAM_TIMEOUT" in error_message:
        return "🔊 Audio processing timed out. Please try again with a shorter audio or check your connection."
    elif "DEEPGRAM_CONNECTION_ERROR" in error_message:
        return "🔊 Unable to connect to transcription service. Please check your internet connection."
    elif "DEEPGRAM_BAD_REQUEST" in error_message:
        return "🔊 Invalid audio format or quality. Please try a different audio file."
    elif "DEEPGRAM_" in error_message:
        return "🔊 Audio transcription temporarily unavailable. Please try again later."
    else:
        return "❌ An unexpected error occurred. Please try again."

# Enhanced upload endpoint with better error handling
@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    try:
        print("Received upload request")
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"Processing file: {file.filename}")
        
        # Check if we have Deepgram API key
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        if not deepgram_key:
            return jsonify({'error': '🔊 Audio transcription service not configured. Please contact support.'}), 500
        
        # Save uploaded file temporarily
        file_extension = os.path.splitext(file.filename)[1] or '.mp3'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Determine mimetype for Deepgram
            mimetype = file.content_type or 'audio/mpeg'
            
            # Process audio with Deepgram
            transcript = transcribe_audio_file(temp_file_path, mimetype, "en")
            print(f"Transcript: {transcript}")
            
            # Run fraud detection on the transcript
            input_transformed = vectorizer.transform([transcript]).toarray()
            probabilities = model.predict_proba(input_transformed)
            positive_prob = probabilities[0, 1] if probabilities.shape[1] > 1 else 0.5
            score = 100 - round(positive_prob * 100)
            
            print(f"Fraud score: {score}")
            
            # Get fraud result with reason if needed
            fraud_result = get_fraud_result(transcript, score)
            
            return jsonify({
                'transcript': transcript,
                'fraud_detection': fraud_result,
                'status': 'success'
            })
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file: {cleanup_error}")
            
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        user_friendly_error = get_user_friendly_error(str(e))
        return jsonify({'error': user_friendly_error}), 500

# Enhanced transcribe endpoint with better error handling
@app.route("/transcribe/<language>", methods=["POST"])
def transcribe(language):
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        if not audio_file:
            return jsonify({"error": "Empty file"}), 400
        
        # Check if we have Deepgram API key
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        if not deepgram_key:
            return jsonify({"error": "🔊 Audio transcription service not configured. Please contact support."}), 500
            
        audio_file.seek(0)
        mimetype = audio_file.mimetype
        if language not in ["english", "hindi"]:
            return jsonify({"error": "Unsupported language"}), 400
            
        lang_code = "en" if language == "english" else "hi"
        transcript = transcribe_audio(audio_file, mimetype, lang_code)
        
        text = transcript

        input_transformed = vectorizer.transform([text]).toarray()
        probabilities = model.predict_proba(input_transformed)
        positive_prob = probabilities[0, 1] if probabilities.shape[1] > 1 else 0.5
        score = 100 - round(positive_prob * 100)

        print("score:", score)

        result = get_fraud_result(text, score)
        result["transcript"] = transcript
        return jsonify(result)

    except Exception as e:
        print(f"Error in transcribe endpoint: {str(e)}")
        user_friendly_error = get_user_friendly_error(str(e))
        return jsonify({"error": user_friendly_error}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Fraud Detection API!"})

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        input_text = data.get('text')
        id = data.get('id')

        if not input_text:
            return jsonify({"error": "No input text provided"}), 400
        
        if id not in store:
            store[id] = [input_text]
        else:
            store[id].append(input_text)

        text = ' '.join(store[id])
        print("all text:", text)

        if len(store[id]) > 4:
            store[id].pop(0)

        input_transformed = vectorizer.transform([text]).toarray()
        probabilities = model.predict_proba(input_transformed)
        positive_prob = probabilities[0, 1] if probabilities.shape[1] > 1 else 0.5
        score = 100 - round(positive_prob * 100)

        result = get_fraud_result(text, score)
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in predict endpoint: {str(e)}")
        return jsonify({"error": "Fraud detection temporarily unavailable. Please try again."}), 500

@socketio.on('predict')
def handle_predict_event(data):
    try:
        input_text = data.get('text')
        id = data.get('id')

        print("Received text:", input_text)

        if not input_text:
            emit('error', {"error": "No input text provided"})
            return
        
        if id in store and store[id] and store[id][-1].lower() in input_text.lower():
            print("deleted: ", store[id].pop())
        
        if id not in store:
            store[id] = [input_text]
        else:
            store[id].append(input_text)

        text = ', '.join(store[id])
        print("All text:", text)

        if len(store[id]) > 5:
            store[id].pop(0)

        input_transformed = vectorizer.transform([text]).toarray()
        probabilities = model.predict_proba(input_transformed)
        positive_prob = probabilities[0, 1] if probabilities.shape[1] > 1 else 0.5
        score = 100 - round(positive_prob * 100)

        result = get_fraud_result(text, score)
        emit('prediction', result)
        
    except Exception as e:
        print(f"Error in socket predict: {str(e)}")
        emit('error', {"error": "🤖 Fraud detection temporarily unavailable. Please try again."})

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)