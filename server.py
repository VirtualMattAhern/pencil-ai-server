from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Create OpenAI client using environment variable for API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("input", "")

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",  # Or "gpt-3.5-turbo" if needed
            messages=[
                {"role": "system", "content": "You are a pencil-selling AI expert, who wants to help make customers happy with the most durable, reliable and best pencil available. Follow all business logic."},
                {"role": "user", "content": user_input}
            ]
        )
    reply = completion.choices[0].message["content"]
    return jsonify({"response": reply})

  except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
