
import os
import yaml
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY2")

app = Flask(__name__)
CORS(app)
app.debug = True

# Load PRR rules from YAML
with open("prr_rules.yaml", "r") as f:
    prr_rules = yaml.safe_load(f)

persona = prr_rules.get("default_persona", "Edgar Allan Poe")
purchase_flow = prr_rules["purchase_flow"]

# Connect to SQLite
db_path = "hybrid_ai_app.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def deduct_inventory(product_name):
    cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE LOWER(name) = LOWER(?)", (product_name,))
    conn.commit()

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("message", "").strip()
    session = request.json.get("session", {})
    history = session.get("history", [])
    persona = session.get("persona", prr_rules.get("default_persona", "Edgar Allan Poe"))

    print(f"[DEBUG] Incoming user input: {user_input}")
    print(f"[DEBUG] Current session state: {session}")

    for step in purchase_flow:
        step_type = step.get("type")
        step_key = step.get("key")

        if step_key in session:
            continue

        if step_type == "prompt":
            print(f"[DEBUG] Prompting user for: {step_key}")
            return jsonify({"response": f"{persona}: {step['text']}", "session": session})

        elif step_type == "capture":
            print(f"[DEBUG] Attempting to capture value for: {step_key}")
            history.append({"role": "user", "content": user_input})
            messages = [
                {"role": "system", "content": f"You are {persona}. Your task is to extract the value for '{step_key}' from the user's message."}
            ] + history

            try:
                completion = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                extracted_value = completion.choices[0].message.content.strip()
                print(f"[DEBUG] Extracted value for {step_key}: {extracted_value}")
            except Exception as e:
                print(f"[ERROR] OpenAI extraction failed: {e}")
                extracted_value = ""

            if not extracted_value:
                return jsonify({"response": f"{persona}: I'm sorry, I couldn't understand that. Could you rephrase?", "session": session})

            session[step_key] = extracted_value
            session["history"] = history
            return jsonify({"response": f"{persona}: {step['confirmation']} {extracted_value}", "session": session})

        elif step_type == "action" and step.get("action") == "deduct_inventory":
            product = session.get("product", "")
            if product:
                deduct_inventory(product)
                print(f"[DEBUG] Deducted inventory for: {product}")
                return jsonify({"response": f"{persona}: {step['success']}", "session": session})

    return jsonify({"response": f"{persona}: I could not understand that request.", "session": session})

@app.route("/inventory", methods=["GET"])
def inventory():
    cursor.execute("SELECT name, quantity FROM inventory")
    rows = cursor.fetchall()
    return jsonify({"inventory": [{"name": row[0], "quantity": row[1]} for row in rows]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
