import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI

import db as dbx
from context import SYSTEM_PROMPT

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing in .env")

client = OpenAI(api_key=API_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")
CORS(app, supports_credentials=True)

# create tables at startup
dbx.create_tables()

# helpers
def require_login():
    if "user_id" not in session:
        return False, jsonify({"error": "Unauthorized"}), 401
    return True, None, None

# Auth
@app.post("/register")
def register():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if dbx.get_user_by_username(username):
        return jsonify({"error": "username already exists"}), 400
    user_id = dbx.insert_user(username, generate_password_hash(password))
    return jsonify({"message": "registered", "user_id": user_id}), 200

@app.post("/login")
def login():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    user = dbx.get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]

    sessions_with_msgs = dbx.get_user_sessions_with_messages(user["id"])
    latest_session_id = sessions_with_msgs[0]["id"] if sessions_with_msgs else None
    latest_messages = sessions_with_msgs[0]["messages"] if sessions_with_msgs else []

    return jsonify({
        "message": "ok",
        "user_id": user["id"],
        "username": user["username"],
        "sessions": sessions_with_msgs,
        "latest_session_id": latest_session_id,
        "latest_messages": latest_messages
    }), 200

@app.get("/logout")
def logout():
    session.clear()
    return jsonify({"message": "logged out"}), 200

@app.get("/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    return jsonify({"id": session["user_id"], "username": session["username"]}), 200

# sessions
@app.get("/sessions")
def list_sessions():
    ok, err, code = require_login()
    if not ok: return err, code
    user_id = session["user_id"]
    rows = dbx.list_sessions_with_preview(user_id)
    out = []
    for r in rows:
        title = r.get("first_user_message") or r.get("session_name") or f"Chat {r['id']}"
        if title and len(title) > 60:
            title = title[:60] + "…"
        out.append({
            "id": r["id"],
            "title": title,
            "session_name": r.get("session_name"),
            "started_at": r["started_at"],
            "last_activity": r.get("last_activity")
        })
    return jsonify({"sessions": out}), 200

@app.post("/sessions")
def create_new_session():
    ok, err, code = require_login()
    if not ok: return err, code
    user_id = session["user_id"]
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "New Chat").strip()
    sid = dbx.create_session(user_id, session_name=name)
    return jsonify({"session_id": sid}), 200

@app.get("/sessions/<int:session_id>/messages")
def get_session_messages(session_id: int):
    ok, err, code = require_login()
    if not ok: return err, code
    user_id = session["user_id"]
    if not dbx.session_belongs_to_user(session_id, user_id):
        return jsonify({"error": "not found"}), 404
    messages = dbx.get_chats_for_session(session_id)
    return jsonify({"messages": messages}), 200

# chat
@app.post("/chat")
def chat():
    ok, err, code = require_login()
    if not ok: return err, code
    data = request.get_json(force=True) or {}
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id")
    if not user_message:
        return jsonify({"error": "message is required"}), 400
    user_id = session["user_id"]
    if session_id:
        if not dbx.session_belongs_to_user(session_id, user_id):
            return jsonify({"error": "invalid session"}), 400
    else:
        session_id = dbx.create_session(user_id, "New Chat")

    # Build history
    history = dbx.get_history_pairs(session_id)
    summary = dbx.get_session_summary(session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if summary:
        messages.append({"role": "system", "content": f"Summary of previous conversation:\n{summary}"})

    # include last 10 chat pairs to keep context
    for m in history[-20:]:
        messages.append({"role": m["role"], "content": m["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=OPEN_AI_MODEL,
            messages=messages,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content
        chat_id = dbx.insert_chat(session_id, user_message, answer, feedback=None)

        # Update session summary for memory
        summary_prompt = f"""
        Summarize the following conversation in a structured, chronological timeline for future reference. 
        Keep it concise but preserve the order of what the user asked and how the assistant responded. 
        Do not merge or rephrase the sequence into a single narrative—use numbered steps.

        Previous summary:
        {summary or "None"}

        New conversation:
        User: {user_message}
        Assistant: {answer}
        """

        summary_resp = client.chat.completions.create(
            model=OPEN_AI_MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.0,
        )
        summary_text = summary_resp.choices[0].message.content
        dbx.update_session_summary(session_id, summary_text)

        return jsonify({"response": answer, "chat_id": chat_id, "session_id": session_id}), 200
    except Exception as e:
        print("Chat error:", e)
        return jsonify({"error": str(e)}), 500


# feedback
@app.post("/feedback")
def feedback():
    ok, err, code = require_login()
    if not ok: return err, code
    data = request.get_json(force=True) or {}
    chat_id = data.get("chat_id")
    feedback_val = (data.get("feedback") or "").strip().lower()
    if feedback_val not in ("liked", "disliked"):
        return jsonify({"error": "feedback must be 'liked' or 'disliked'"}), 400
    if not chat_id:
        return jsonify({"error": "chat_id required"}), 400
    try:
        dbx.update_feedback(chat_id, feedback_val)
        return jsonify({"message": "feedback saved"}), 200
    except Exception as e:
        print("Feedback error:", e)
        return jsonify({"error": str(e)}), 500

@app.get("/health")
def health():
    return {"ok": True, "model": OPEN_AI_MODEL}, 200

if __name__ == "__main__":
    print("✅ Flask backend at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
