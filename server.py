
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

persona_map = prr_rules["persona_rules"]
purchase_flow = prr_rules["purchase_flow"]
fallback_enabled = prr_rules.get("fallback_to_llm", True)

db_path = "hybrid_ai_app.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def get_persona_for_product(product_name):
    for rule in persona_map:
        if rule["product"].lower() in product_name.lower():
            return rule["persona"]
    return "Default Persona"

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
                session["persona"] = persona
                session["product"] = rule["product"]
                break

    # Check for active prompt key
    active_key = session.get("active_prompt")
    if active_key:
        print(f"[debug] Capturing response for prompt key: {active_key}")
        session[active_key] = user_input
        session.pop("active_prompt", None)

    # Go through purchase flow rules
    for step in purchase_flow:
        step_type = step.get("type")
        step_key = step.get("key")

        if step_type == "prompt" and step_key not in session:
            session["active_prompt"] = step_key
            return jsonify({"response": f"{persona}: {step['text']}", "session": session})

        elif step_type == "action" and step.get("action") == "deduct_inventory":
            product = session.get("product", "")
            deduct_inventory(product)
            return jsonify({"response": f"{persona}: {step['success']}", "session": session})

    # Fallback to OpenAI LLM
    if fallback_enabled:
        completion = openai.chat.completions.create(
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
