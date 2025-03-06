from flask import Flask, render_template, request, jsonify, send_file
import openai
import os
from flask_cors import CORS
import io
import traceback  # ✅ Added for detailed error logging

app = Flask(__name__, template_folder="templates")  
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

conversation_history = []
response_style = ""
initial_text = ""
is_setup_complete = False  

@app.route("/")
def home():
    global is_setup_complete
    if not is_setup_complete:
        return render_template("setup.html")  
    return render_template("index.html")  

@app.route("/setup", methods=["POST"])
def setup_tutor():
    """Receives tutor behavior and initial conversation text from the instructor."""
    global conversation_history, response_style, initial_text, is_setup_complete
    
    try:
        # ✅ Log incoming request data
        print("📥 Incoming /setup request:", request.data)

        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON input"}), 400
        
        response_style = data.get("response_style", "").strip()
        initial_text = data.get("initial_text", "").strip()

        if not response_style or not initial_text:
            return jsonify({"error": "Missing tutor setup fields."}), 400

        # ✅ Initialize conversation history
        conversation_history = [
            {"role": "system", "content": f"You are a tutor using the {response_style} method. Guide the student accordingly."},
            {"role": "assistant", "content": initial_text}
        ]

        is_setup_complete = True  # ✅ Mark setup as complete

        # ✅ Log the setup completion
        print(f"✔ Tutor setup completed: Style = {response_style}, Initial Text = {initial_text}")

        return jsonify({
            "response": "Tutor setup successful!",
            "response_style": response_style,
            "initial_text": initial_text
        })

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ ERROR in /setup: {error_details}")  # ✅ Print full error traceback
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/get_initial_text", methods=["GET"])
def get_initial_text():
    global is_setup_complete, initial_text
    if not is_setup_complete:
        return jsonify({"initial_text": ""})  
    return jsonify({"initial_text": initial_text})

@app.route("/ask", methods=["POST"])
def ask():
    global is_setup_complete
    
    if not is_setup_complete:
        return jsonify({"response": "Error: The tutor has not been set up yet. Please enter tutor settings first."}), 400

    try:
        data = request.get_json()
        question = data["question"]
        
        conversation_history.append({"role": "user", "content": question})
        
        answer = ask_chatgpt(conversation_history)
        
        conversation_history.append({"role": "assistant", "content": answer})
        
        return jsonify({"response": answer})

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ ERROR in /ask: {error_details}")  # ✅ Log the exact error
        return jsonify({"response": f"Server Error: {str(e)}"}), 500

def ask_chatgpt(conversation):
    """Sends conversation history to OpenAI API and returns a response using GPT-4."""
    try:
        response = openai.ChatCompletion.create(  
            model="gpt-4",
            messages=conversation
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  
    app.run(host="0.0.0.0", port=port, debug=True)
