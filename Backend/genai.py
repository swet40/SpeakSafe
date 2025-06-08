import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

def gen_ai_json(input_text):
    prompt = (
        "You are an AI fraud detection assistant.\n"
        "Given the following phone call transcript, analyze whether it is a fraud attempt.\n"
        "Respond ONLY in a valid JSON format with two keys:\n"
        "- \"fraud_probability\": integer between 0 and 100\n"
        "- \"reason\": a short explanation (2-5 sentences max)\n\n"
        "Do NOT include markdown, code blocks, or extra commentary.\n\n"
        f"Transcript:\n{input_text}\n\n"
        "Respond in JSON only:"
    )

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        print("Raw Gemini response (as text):", repr(raw_text))

        # Remove markdown/code block wrappers if any
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()

        # Try parsing JSON directly
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            print("Direct JSON parse failed. Trying regex fallback.")
            import re
            match = re.search(r'\{[\s\S]*?\}', raw_text)
            if match:
                parsed = json.loads(match.group(0))
            else:
                raise ValueError("No JSON object found.")

        reason = parsed.get("reason", "No reason provided")
        return {
            "reason": reason
        }

    except Exception as e:
        print("Gemini API Error:", str(e))
        return {"reason": "AI error in analysis"}
