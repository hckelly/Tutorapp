from flask import Flask, request, jsonify, send_file
import openai
import os
from flask_cors import CORS
import io

app = Flask(__name__)
CORS(app)

# ✅ Ensure API key is loaded securely
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Store tutor configuration
conversation_history = []
response_style = ""
initial_text = ""
is_setup_complete = False  # Prevent student questions before setup

@app.route("/setup", methods=["POST"])
def setup_tutor():
    """88Receives tutor behavior and initial conversation text from the instructor."""
    global conversation_history, response_style, initial_text, is_setup_complete
    
    data = request.get_json()
    response_style = data.get("response_style", "").strip()
    initial_text = data.get("initial_text", "").strip()

    if not response_style or not initial_text:
        return jsonify({"response": "Error: Missing tutor setup fields."}), 400

    # ✅ Initialize conversation history with instructor-provided settings
    conversation_history = [
        {"role": "system", "content": f"You are a tutor using the {response_style} method. Guide the student accordingly."},
        {"role": "assistant", "content": initial_text}
    ]

    is_setup_complete = True

    # ✅ Preload a dummy TTS request to reduce cold start lag
    preload_speech("Welcome to the AI Tutor!")

    return jsonify({"response": "Tutor setup successful!", "response_style": response_style, "initial_text": initial_text})

def ask_chatgpt(conversation):
    """Sends conversation history to OpenAI API and returns a response."""
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/ask", methods=["POST"])
def ask():
    """Handles student questions and returns AI response."""
    global is_setup_complete
    
    if not is_setup_complete:
        return jsonify({"response": "Error: The tutor has not been set up yet. Please enter tutor settings first."}), 400

    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"response": "Error: Missing 'question' field in request."}), 400
        
        question = data["question"]
        
        # ✅ Add student's question to conversation history
        conversation_history.append({"role": "user", "content": question})
        
        # ✅ Get AI's response
        answer = ask_chatgpt(conversation_history)
        
        # ✅ Add AI response to conversation history
        conversation_history.append({"role": "assistant", "content": answer})
        
        return jsonify({"response": answer})

    except Exception as e:
        return jsonify({"response": f"Server Error: {str(e)}"}), 500

@app.route("/speak", methods=["POST"])
def speak():
    """Generates speech from text using OpenAI TTS."""
    try:
        data = request.get_json()
        text = data.get("text", "")
        voice = data.get("voice", "alloy")

        response = openai.audio.speech.create(
            model="tts-1",  # ✅ Faster model
            voice=voice,
            input=text,
        )

        # ✅ Stream response as audio file
        audio_data = io.BytesIO(response.content)
        return send_file(audio_data, mimetype="audio/mpeg")

    except Exception as e:
        return jsonify({"error": f"Speech synthesis failed: {str(e)}"}), 500

def preload_speech(text):
    """Preloads a dummy speech request to reduce latency."""
    try:
        openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
    except Exception as e:
        print(f"Preload failed: {e}")

if __name__ == "__main__":
    print("Tutor system ready. Please set up the tutor using the web interface.")
    app.run(debug=True)
