from flask import Flask, render_template, request, jsonify, send_file
import openai
import os
from flask_cors import CORS
import io

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
    global conversation_history, response_style, initial_text, is_setup_complete
    
    data = request.get_json()
    response_style = data.get("response_style", "").strip()
    initial_text = data.get("initial_text", "").strip()

    if not response_style or not initial_text:
        return jsonify({"response": "Error: Missing tutor setup fields."}), 400

    conversation_history = [
        {"role": "system", "content": f"You are a tutor using the {response_style} method. Guide the student accordingly."},
        {"role": "assistant", "content": initial_text}
    ]

    is_setup_complete = True  

    speak_text(initial_text)

    return jsonify({
        "response": "Tutor setup successful!",
        "response_style": response_style,
        "initial_text": initial_text  
    })

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
        return jsonify({"response": f"Server Error: {str(e)}"}), 500

def ask_chatgpt(conversation):
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
