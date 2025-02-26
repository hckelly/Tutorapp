from flask import Flask, request, jsonify, render_template, send_file
import openai
import os
import requests
from flask_cors import CORS
import io

# ✅ Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # Allow frontend to communicate with backend

# ✅ Load API key securely from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Store tutor settings
conversation_history = []
response_style = ""
initial_text = ""
is_setup_complete = False  # Prevent student questions before setup

@app.route("/")
def home():
    """Serve the index.html file for the frontend."""
    return render_template("index.html")

@app.route("/setup", methods=["POST"])
def setup_tutor():
    """Receives tutor behavior and initial conversation text from the instructor."""
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
    return jsonify({"response": "Tutor setup successful!", "response_style": response_style, "initial_text": initial_text})

def ask_chatgpt(conversation):
    """Sends conversation history to OpenAI API and returns a response."""
    try:
        client = openai.OpenAI()  # ✅ Uses the new OpenAI API format
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

@app.route("/reset", methods=["POST"])
def reset_session():
    """Resets the session by updating the initial_text and clearing conversation history."""
    global conversation_history, initial_text
    
    data = request.get_json()
    new_initial_text = data.get("initial_text", "").strip()

    if not is_setup_complete:
        return jsonify({"response": "Error: The tutor has not been set up yet. Please enter tutor settings first."}), 400

    if not new_initial_text:
        return jsonify({"response": "Error: Missing new initial conversation text."}), 400

    # ✅ Update initial_text with new input from instructor
    initial_text = new_initial_text

    # ✅ Reset conversation history with updated initial_text
    conversation_history = [
        {"role": "system", "content": f"You are a tutor using the {response_style} method. Guide the student accordingly."},
        {"role": "assistant", "content": initial_text}
    ]
    
    return jsonify({"response": "Session reset!", "initial_text": initial_text})

@app.route("/speak", methods=["POST"])
def speak():
    """Handles text-to-speech conversion securely using OpenAI API."""
    data = request.get_json()
    text = data.get("text", "")
    voice = data.get("voice", "alloy")  # Default to 'alloy'

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {openai.api_key}",
                "Content-Type": "application/json"
            },
            json={"model": "tts-1", "voice": voice, "input": text},
            stream=True
        )

        if response.status_code == 200:
            return send_file(io.BytesIO(response.content), mimetype="audio/mp3")
        else:
            return jsonify({"error": "OpenAI API Error", "details": response.text}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Tutor system ready. Please set up the tutor using the web interface.")
    app.run(debug=True)
