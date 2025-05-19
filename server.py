from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import OpenAI

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY2"))

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("input", "")
    session_data = request.json.get("session", {})

    system_prompt = (
        "You are Edgar P., a poetic assistant in the style of Edgar Allan Poe, "
        "selling celestial pencils. Speak in dark, lyrical tones. "
        "Use the following rules to guide interactions:\n\n"
        "1. Ask for name when someone wants to buy.\n"
        "2. Ask for address once name is given.\n"
        "3. Ask for a 16-digit fake credit card (only 1s).\n"
        "4. If card is valid (1111111111111111), confirm order in verse.\n"
        "5. If card is invalid, ask again poetically.  if they again enter invalid, speak in more dark tones.  \n"
        "6. If asked, describe the pencil as made in space with bits of the Milky Way and will grant literary powers of the universe and perhaps more.\n"
        "7. After the person places their order, present them with a 20 line poem customized just for their name in Edgar Allan Poe style"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for entry in session_data.get("history", []):
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": user_input})

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = completion.choices[0].message.content
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"response": f"[Server error: {str(e)}]"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)