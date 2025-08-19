import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from context import SYSTEM_PROMPT

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing in .env")
client = OpenAI(api_key=API_KEY)

app = Flask(__name__)
CORS(app) 

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not user_message:
            return jsonify({"error": "message is required"}), 400

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
        )
        answer = resp.choices[0].message.content
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # keep debug=False to avoid the werkzeug debug console import issue
    print("✅ Flask backend listening on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
