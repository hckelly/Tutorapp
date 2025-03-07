"""
AI Tutor Flask Application

This application allows an instructor to set up an AI-powered tutor 
that interacts with students using OpenAI's GPT-4.
"""

import os
import traceback
from flask import Flask, render_template, request, jsonify, send_file
import openai
import io
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__, template_folder="templates")  
CORS(app)

# Global Variables
RESPONSE_STYLE = ""
INITIAL_TEXT = ""
IS_SETUP_COMPLETE = False
CONVERSATION_HISTORY = []

# Ensure OpenAI API key is loaded
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/")
def home():
    """Route to serve the appropriate page based on setup status."""
    global IS_SETUP_COMPLETE
    if not IS_SETUP_COMPLETE:
        return render_template("setup.html")  # ✅ Instructor setup first
    return render_template("index.html")  # ✅ Then show student page


@app.route("/setup", methods=["POST"])
def setup_tutor():
    """Receives tutor behavior and initial conversation text from the instructor."""
    global RESPONSE_STYLE, INITIAL_TEXT, IS_SETUP_COMPLETE, CONVERSATION_HISTORY

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON input"}), 400

        response_style = data.get("response_style", "").strip()
        initial_text = data.get("initial_text", "").strip()

        if not response_style or not initial_text:
            return jsonify({"error": "Missing tutor setup fields."}), 400

        # Set global variables
        RESPONSE_STYLE = response_style
        INITIAL_TEXT = initial_text
        IS_SETUP_COMPLETE = True

        # Initialize conversation history
        CONVERSATION_HISTORY = [
            {"role": "system", "content": f"You are a tutor using the {RESPONSE_STYLE} method. Guide the student accordingly."},
            {"role": "assistant", "content": INITIAL_TEXT}
        ]

        return jsonify({
            "response": "Tutor setup successful!",
            "response_style": RESPONSE_STYLE,
            "initial_text": INITIAL_TEXT
        })

    except Exception as error:
        print(f"❌ ERROR in /setup: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(error)}"}), 500


@app.route("/get_initial_text", methods=["GET"])
def get_initial_text():
    """Returns the initial text for the student page in JSON format."""
    global IS_SETUP_COMPLETE, INITIAL_TEXT
    if not IS_SETUP_COMPLETE:
        return jsonify({"initial_text": ""})  # ✅ Always return valid JSON
    return jsonify({"initial_text": INITIAL_TEXT})


@app.route("/ask", methods=["POST"])
def ask():
    """Handles student queries and returns AI-generated responses."""
    if not IS_SETUP_COMPLETE:
        return jsonify({"response": "Error: The tutor has not been set up yet. Please enter tutor settings first."}), 400

    try:
        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"response": "Error: No question provided."}), 400

        # Append user question to conversation history
        CONVERSATION_HISTORY.append({"role": "user", "content": question})

        # Get AI response
        answer = ask_chatgpt(CONVERSATION_HISTORY)

        # Append AI response to history
        CONVERSATION_HISTORY.append({"role": "assistant", "content": answer})

        return jsonify({"response": answer})

    except Exception as error:
        print(f"❌ ERROR in /ask: {traceback.format_exc()}")
        return jsonify({"response": f"Server Error: {str(error)}"}), 500


def ask_chatgpt(conversation):
    """Sends conversation history to OpenAI API and returns a response using GPT-4."""
    try:
        client = openai.OpenAI()  # ✅ Fix: Remove 'proxies' argument
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation
        )
        return response.choices[0].message.content

    except Exception as error:
        print(f"❌ ERROR in AI Response: {traceback.format_exc()}")
        return f"Error: {str(error)}"


@app.route("/speak", methods=["POST"])
def generate_speech():
    """Converts AI response text to speech and returns an audio file."""
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "alloy")  # Default voice: alloy

        if not text:
            return jsonify({"error": "No text provided for speech"}), 400

        client = openai.OpenAI()
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        # ✅ Fix: Stream the audio properly
        audio_file = io.BytesIO(response.content)  # Read the audio stream
        audio_file.seek(0)
        return send_file(audio_file, mimetype="audio/mpeg")

    except Exception as error:
        print(f"❌ ERROR in /speak: {traceback.format_exc()}")
        return jsonify({"error": f"Speech synthesis error: {str(error)}"}), 500


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    HOST = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"  # ✅ Fix for Render & Local
    app.run(host=HOST, port=PORT, debug=True)
