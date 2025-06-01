import os
import yaml
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai  # correct OpenAI SDK import
from dotenv import load_dotenv

load_dotenv()  # load .env vars like OPENAI_API_KEY
openai.api_key = os.getenv("OPENAI_API_KEY2")

app = Flask(__name__)
CORS(app)  # allow frontend access
app.debug = True

# Load PRR rules from YAML
with open("prr_rules.yaml", "r") as f:
    prr_rules = yaml.safe_load(f)

# Load persona mapping from PRR
persona_map = prr_rules["persona_rules"]
purchase_flow = prr_rules["purchase_flow"]
fallback_enabled = prr_rules.get("fallback_to_llm", True)

# Connect to SQLite
db_path = "hybrid_ai_app.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Get persona based on inventory selection
def get_persona_for_product(product_name):
    for rule in persona_map:
        if rule["product"].lower() in product_name.lower():
            return rule["persona"]
    return "Default Persona"

# Placeholder: simulate inventory deduction
def deduct_inventory(product_name):
    cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE LOWER(name) = LOWER(?)", (product_name,))
    conn.commit()

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("message", "").strip()
    session = request.json.get("session", {})
    history = session.get("history", [])
    persona = session.get("persona", None)

    # Persona switching based on purchase intent
    if "buy" in user_input.lower():
        for rule in persona_map:
            if rule["product"].lower() in user_input.lower():
                persona = rule["persona"]
                break

    # Process step-by-step prompts
    for step in purchase_flow:
        step_type = step.get("type")
        step_key = step.get("key")

        if step_type == "prompt" and step_key not in session:
            return jsonify({"response": f"{persona}: {step['text']}", "session": session})

        elif step_type == "capture" and step_key not in session:
            session[step_key] = user_input
            return jsonify({"response": f"{persona}: {step['confirmation']}", "session": session})

        elif step_type == "action" and step.get("action") == "deduct_inventory":
            product = session.get("product", "")
            deduct_inventory(product)
            return jsonify({"response": f"{persona}: {step['success']}", "session": session})

    # If no matching rule or finished all steps, fallback to LLM
    if fallback_enabled:
        openai_key = os.getenv("OPENAI_API_KEY2")
        if not openai_key:
            return jsonify({"response": f"{persona}: [OpenAI key missing]"})
        
        client = OpenAI(api_key=openai_key)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are {persona}. Answer poetically and eloquently."},
                {"role": "user", "content": user_input}
            ]
        )
        reply = completion.choices[0].message.content
        return jsonify({"response": f"{persona}: {reply}", "session": session})

    return jsonify({"response": f"{persona}: I could not understand that request."})

@app.route("/inventory", methods=["GET"])
def inventory():
    cursor.execute("SELECT name, quantity FROM inventory")
    rows = cursor.fetchall()
    return jsonify({"inventory": [{"name": row[0], "quantity": row[1]} for row in rows]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)