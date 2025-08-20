import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "icd_chatbot"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )

def create_tables():
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS chat_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_name VARCHAR(255),
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS chats (
        id SERIAL PRIMARY KEY,
        session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        user_message TEXT,
        ai_response TEXT,
        feedback VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
    finally:
        conn.close()

# -------------------------
# Users
# -------------------------
def get_user_by_username(username: str) -> Dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            return cur.fetchone()
    finally:
        conn.close()

def insert_user(username: str, password_hash: str) -> int:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                    (username, password_hash),
                )
                return cur.fetchone()[0]
    finally:
        conn.close()

# -------------------------
# Sessions
# -------------------------
def create_session(user_id: int, session_name: str | None = None) -> int:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s) RETURNING id",
                    (user_id, session_name),
                )
                return cur.fetchone()[0]
    finally:
        conn.close()

def session_belongs_to_user(session_id: int, user_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM chat_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
            return cur.fetchone() is not None
    finally:
        conn.close()

def get_latest_session_id(user_id: int) -> int | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM chat_sessions WHERE user_id=%s ORDER BY started_at DESC, id DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

def list_sessions_with_preview(user_id: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT
      cs.id,
      cs.session_name,
      cs.started_at,
      (SELECT c.user_message
         FROM chats c
        WHERE c.session_id = cs.id
          AND c.user_message IS NOT NULL
        ORDER BY c.created_at ASC, c.id ASC
        LIMIT 1) AS first_user_message,
      (SELECT MAX(c.created_at)
         FROM chats c
        WHERE c.session_id = cs.id) AS last_activity
    FROM chat_sessions cs
    WHERE cs.user_id = %s
    ORDER BY COALESCE(
               (SELECT MAX(c.created_at) FROM chats c WHERE c.session_id = cs.id),
               cs.started_at
             ) DESC, cs.id DESC;
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()
    finally:
        conn.close()

# -------------------------
# Chats / Messages
# -------------------------
def insert_chat(session_id: int, user_message: str, ai_response: str, feedback: str | None = None) -> int:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chats (session_id, user_message, ai_response, feedback) VALUES (%s, %s, %s, %s) RETURNING id",
                    (session_id, user_message, ai_response, feedback),
                )
                return cur.fetchone()[0]
    finally:
        conn.close()

def get_history_pairs(session_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_message, ai_response, id FROM chats WHERE session_id=%s ORDER BY created_at ASC, id ASC", (session_id,))
            rows = cur.fetchall()
            messages = []
            for r in rows:
                if r["user_message"]:
                    messages.append({"role": "user", "content": r["user_message"], "chat_id": r["id"]})
                if r["ai_response"]:
                    messages.append({"role": "assistant", "content": r["ai_response"], "chat_id": r["id"]})
            return messages
    finally:
        conn.close()

def get_chats_for_session(session_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, user_message, ai_response, feedback, created_at FROM chats WHERE session_id=%s ORDER BY created_at ASC, id ASC", (session_id,))
            rows = cur.fetchall()
            out = []
            for r in rows:
                if r["user_message"]:
                    out.append({"role": "user", "content": r["user_message"], "chat_id": r["id"], "feedback": None})
                if r["ai_response"]:
                    out.append({"role": "assistant", "content": r["ai_response"], "chat_id": r["id"], "feedback": r.get("feedback")})
            return out
    finally:
        conn.close()

def update_feedback(chat_id: int, feedback: str):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE chats SET feedback=%s WHERE id=%s", (feedback, chat_id))
    finally:
        conn.close()

# -------------------------
# New helper: sessions + messages for a user (used on login)
# -------------------------
def get_user_sessions_with_messages(user_id: int) -> List[Dict[str, Any]]:
    sessions = list_sessions_with_preview(user_id)
    out = []
    for s in sessions:
        sid = s["id"]
        chats = get_chats_for_session(sid)
        title = s.get("first_user_message") or s.get("session_name") or f"Chat {sid}"
        out.append({
            "id": sid,
            "session_name": s.get("session_name"),
            "title": title,
            "started_at": s.get("started_at"),
            "first_user_message": s.get("first_user_message"),
            "last_activity": s.get("last_activity"),
            "messages": chats
        })
    return out
