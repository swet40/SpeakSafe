from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import joblib
import os
import json
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
