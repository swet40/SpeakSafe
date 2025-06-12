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

def transcribe_audio(audio_file, mimetype, language="en"):
    """Transcribe audio using Deepgram API"""
    url = f"https://api.deepgram.com/v1/listen?language={language}"
    headers = {
        "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
        "Content-Type": mimetype,
    }
    try:
        response = requests.post(url, data=audio_file.read(), headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if (result
            and "results" in result 
            and "channels" in result["results"]
            and len(result["results"]["channels"]) > 0
            and "alternatives" in result["results"]["channels"][0]
            and len(result["results"]["channels"][0]["alternatives"]) > 0
            and "transcript" in result["results"]["channels"][0]["alternatives"][0]):
            return result["results"]["channels"][0]["alternatives"][0]["transcript"]
        else:
            raise ValueError("Invalid response structure from Deepgram API")
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        print(f"Response content: {response.content if 'response' in locals() else 'No response'}")
        raise

def transcribe_audio_file(file_path, mimetype, language="en"):
    """Transcribe audio file from file path using Deepgram API"""
    url = f"https://api.deepgram.com/v1/listen?language={language}"
    headers = {
        "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
        "Content-Type": mimetype,
    }
    try:
        with open(file_path, 'rb') as audio_file:
            response = requests.post(url, data=audio_file, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if (result
            and "results" in result 
            and "channels" in result["results"]
            and len(result["results"]["channels"]) > 0
            and "alternatives" in result["results"]["channels"][0]
            and len(result["results"]["channels"][0]["alternatives"]) > 0
            and "transcript" in result["results"]["channels"][0]["alternatives"][0]):
            return result["results"]["channels"][0]["alternatives"][0]["transcript"]
        else:
            raise ValueError("Invalid response structure from Deepgram API")
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        print(f"Response content: {response.content if 'response' in locals() else 'No response'}")
        raise

def get_fraud_result(text, score):
    """Generate fraud detection result with reason if score >= 75"""
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
            print("Error parsing AI response:", e)
            result = {
                "fraud_probability": score,
                "reason": "AI error in analysis"
            }

        return result

    return {
        "fraud_probability": score,
        "reason": ""
    }

# NEW ENDPOINT: Upload audio file for fraud detection
# Replace your upload_audio function with this debug version

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    print("=== UPLOAD AUDIO DEBUG ===")
    try:
        print("1. Received upload request")
        print(f"Request method: {request.method}")
        print(f"Request files: {list(request.files.keys())}")
        
        if 'audio' not in request.files:
            print("ERROR: No 'audio' key in request.files")
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        print(f"2. File object: {file}")
        print(f"   Filename: {file.filename}")
        print(f"   Content type: {file.content_type}")
        
        if file.filename == '':
            print("ERROR: Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"3. Processing file: {file.filename}")
        
        # Check if we have Deepgram API key
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        if not deepgram_key:
            print("ERROR: No Deepgram API key found")
            return jsonify({'error': 'Deepgram API key not configured'}), 500
        
        print(f"4. Deepgram API key found: {deepgram_key[:10]}...")
        
        # Save uploaded file temporarily
        file_extension = os.path.splitext(file.filename)[1] or '.mp3'
        print(f"5. File extension: {file_extension}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            print(f"6. Created temp file: {temp_file.name}")
            file.save(temp_file.name)
            temp_file_path = temp_file.name
            file_size = os.path.getsize(temp_file_path)
            print(f"7. Saved file size: {file_size} bytes")
        
        try:
            # Determine mimetype for Deepgram
            mimetype = file.content_type or 'audio/mpeg'
            print(f"8. Using mimetype: {mimetype}")
            
            # Process audio with Deepgram
            print("9. Starting Deepgram transcription...")
            transcript = transcribe_audio_file(temp_file_path, mimetype, "en")
            print(f"10. Transcript received: {transcript[:100]}..." if transcript else "10. No transcript received")
            
            if not transcript or transcript.strip() == "":
                print("ERROR: Empty transcript")
                return jsonify({
                    'error': 'No speech detected in the audio file'
                }), 400
            
            print("11. Running fraud detection...")
            # Run fraud detection on the transcript
            input_transformed = vectorizer.transform([transcript]).toarray()
            probabilities = model.predict_proba(input_transformed)
            positive_prob = probabilities[0, 1] if probabilities.shape[1] > 1 else 0.5
            score = 100 - round(positive_prob * 100)
            
            print(f"12. Fraud score calculated: {score}")
            
            # Get fraud result with reason if needed
            fraud_result = get_fraud_result(transcript, score)
            print(f"13. Fraud result: {fraud_result}")
            
            response_data = {
                'transcript': transcript,
                'fraud_detection': fraud_result,
                'status': 'success'
            }
            print(f"14. Returning response: {response_data}")
            return jsonify(response_data)
            
        except Exception as inner_e:
            print(f"INNER ERROR: {str(inner_e)}")
            import traceback
            traceback.print_exc()
            raise inner_e
            
        finally:
            # Clean up temporary file
            try:
                print(f"15. Cleaning up temp file: {temp_file_path}")
                os.unlink(temp_file_path)
                print("16. Temp file cleaned up successfully")
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")
            
    except Exception as e:
        print(f"OUTER ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process audio file: {str(e)}'}), 500

@app.route("/transcribe/<language>", methods=["POST"])
def transcribe(language):
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        if not audio_file:
            return jsonify({"error": "Empty file"}), 400
            
        audio_file.seek(0)
        mimetype = audio_file.mimetype
        if language not in ["english", "hindi"]:
            return jsonify({"error": "Unsupported language"}), 400
            
        lang_code = "en" if language == "english" else "hi"
        transcript = transcribe_audio(audio_file, mimetype, lang_code)
        
        if not transcript:
            return jsonify({"error": "Failed to transcribe audio"}), 500
            
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
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Fraud Detection API!"})

@app.route('/predict', methods=['POST'])
def predict():
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

@socketio.on('predict')
def handle_predict_event(data):
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

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)