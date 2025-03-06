from flask import Flask, render_template, request, jsonify, send_file
import openai
import os
from flask_cors import CORS
import io

# ✅ Ensure Flask correctly finds the templates folder
app = Flask(__name__, template_folder="templates")  
CORS(app)

# ✅ Securely load API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Store tutor configuration
conversation_history = []
response_style = ""
initial_text = ""
is_setup_complete = False  # Prevent student questions before setup

@app.route("/")
def home():
    """Redirect to setup page if the tutor has not been set up."""
    global is_setup_complete
    if not is_setup_complete:
        return render_template("setup.html")  # ✅ Ensure instructor enters setup first
    return render_template("index.html")  # ✅ Show student page after setup

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

    is_setup_complete = True  # ✅ Mark setup as complete

    # ✅ Speak the initial text immediately when student page loads
    speak_text(initial_text)

    return jsonify({
        "response": "Tutor setup successful!",
        "response_style": response_style,
        "initial_text": initial_text  # ✅ Send initial_text to frontend
    })

@app.route("/get_initial_text", methods=["GET"])
def get_initial_text():
    """Returns the initial text for the student page."""
    global is_setup_complete, initial_text
    if not is_setup_complete:
        return jsonify({"initial_text": ""})  # ✅ Prevent showing text before setup
    return jsonify({"initial_text": initial_text})

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
        
        # ✅ Get AI's response (Always GPT-4)
        answer = ask_chatgpt(conversation_history)
        
        # ✅ Add AI response to conversation history
        conversation_history.append({"role": "assistant", "content": answer})
        
        return jsonify({"response": answer})

    except Exception as e:
        return jsonify({"response": f"Server Error: {str(e)}"}), 500

def ask_chatgpt(conversation):
    """Sends conversation history to OpenAI API and returns a response using GPT-4."""
    try:
        client = openai.OpenAI()  # ✅ Correct new OpenAI v1.0+ client
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation
        )
        return response.choices[0].message.content  # ✅ Updated syntax for OpenAI v1.0+
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/speak", methods=["POST"])
def speak():
    """Generates speech from text using OpenAI TTS."""
    try:
        data = request.get_json()
        text = data.get("text", "")
        voice = data.get("voice", "alloy")

        response = openai.audio.speech.create(
            model="tts-1",  # ✅ Faster TTS model
            voice=voice,
            input=text,
        )

        # ✅ Stream response as audio file
        audio_data = io.BytesIO(response.content)
        return send_file(audio_data, mimetype="audio/mpeg")

    except Exception as e:
        return jsonify({"error": f"Speech synthesis failed: {str(e)}"}), 500

def speak_text(text):
    """Ensures initial_text is spoken."""
    try:
        openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
    except Exception as e:
        print(f"Speech synthesis failed: {e}")

# ✅ Fix for Render Port Configuration
if __name__ == "__main__":
    print("Tutor system ready. Please set up the tutor using the web interface.")
    port = int(os.environ.get("PORT", 10000))  # ✅ Use Render's PORT dynamically
    app.run(host="0.0.0.0", port=port, debug=True)
