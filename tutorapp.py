import os
from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
from openai import OpenAI
import traceback
import tempfile

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Session setup
SESSION_DIR = os.path.join(os.getcwd(), "flask_session")
os.makedirs(SESSION_DIR, exist_ok=True)
app.config["SECRET_KEY"] = str(os.getenv("SECRET_KEY", "fallback_secret"))
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = SESSION_DIR
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = False
Session(app)

# Load OpenAI API key and initialize client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("ERROR: Missing OPENAI_API_KEY in environment!")

client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/")
def home():
    if not session.get("IS_SETUP_COMPLETE"):
        return render_template("setup.html")
    return render_template("index.html")

@app.route("/setup", methods=["POST"])
def setup_tutor():
    try:
        data = request.get_json(force=True)
        print("Received JSON:", data)

        response_style = str(data.get("response_style", "")).strip()
        initial_text = str(data.get("initial_text", "")).strip()
        preferred_voice = str(data.get("preferred_voice", "shimmer")).strip()

        if not response_style or not initial_text:
            return jsonify({"success": False, "message": "Both fields are required."}), 400

        session["IS_SETUP_COMPLETE"] = "true"
        session["response_style"] = response_style
        session["initial_text"] = initial_text
        session["preferred_voice"] = preferred_voice
        session["history"] = [
            {"role": "system", "content": f"You are a helpful tutor who responds in a {response_style} style."},
            {"role": "user", "content": initial_text}
        ]
        session.modified = True

        print("✅ Session updated:", dict(session))

        return jsonify({"success": True, "message": "Setup successful!"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/get_initial_text", methods=["GET"])
def get_initial_text():
    if not session.get("IS_SETUP_COMPLETE"):
        return jsonify({"success": False, "message": "Tutor not set up."}), 400
    return jsonify({"success": True, "initial_text": session.get("initial_text")})

@app.route("/student_reply", methods=["POST"])
def student_reply():
    try:
        data = request.get_json(force=True)
        student_input = str(data.get("message", "")).strip()
        if not student_input:
            return jsonify({"success": False, "message": "Empty input"}), 400

        history = session.get("history", [])
        history.append({"role": "user", "content": student_input})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=history
        )
        ai_reply = response.choices[0].message.content.strip()

        history.append({"role": "assistant", "content": ai_reply})
        session["history"] = history
        session.modified = True

        return jsonify({"success": True, "reply": ai_reply})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/tts", methods=["POST"])
def tts():
    try:
        text = request.json.get("text", "")
        voice = request.json.get("voice") or session.get("preferred_voice", "shimmer")

        if not text:
            return jsonify({"success": False, "message": "No text provided."}), 400

        if voice == "browser":
            return jsonify({"success": True, "message": "Use browser TTS"})

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            ).stream_to_file(temp_audio.name)

            return send_file(temp_audio.name, mimetype="audio/mpeg")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"TTS error: {str(e)}"}), 500

@app.route("/reset", methods=["GET"])
def reset_session():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    print("Flask app running at http://127.0.0.1:10000")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
