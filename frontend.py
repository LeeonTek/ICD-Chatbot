import streamlit as st
import requests

API = "http://127.0.0.1:5000"

st.set_page_config(page_title="ICD Chatbot", page_icon="🩺", layout="wide")

# session state
if "http" not in st.session_state:
    st.session_state.http = requests.Session()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []  # [(role, content, chat_id|None)]
if "active_session" not in st.session_state:
    st.session_state.active_session = None
if "sessions_cache" not in st.session_state:
    st.session_state.sessions_cache = []  # list of {id,title,...}

# API helpers
def api_register(u, p):
    r = st.session_state.http.post(f"{API}/register", json={"username": u, "password": p})
    return r.json(), r.status_code

def api_login(u, p):
    r = st.session_state.http.post(f"{API}/login", json={"username": u, "password": p})
    return r.json(), r.status_code

def api_logout():
    st.session_state.http.get(f"{API}/logout")

def api_list_sessions():
    r = st.session_state.http.get(f"{API}/sessions")
    if r.status_code == 200:
        return r.json().get("sessions", [])
    return []

def api_create_session(name="New Chat"):
    r = st.session_state.http.post(f"{API}/sessions", json={"name": name})
    if r.status_code == 200:
        return r.json().get("session_id")
    return None

def api_get_session_messages(session_id: int):
    r = st.session_state.http.get(f"{API}/sessions/{session_id}/messages")
    if r.status_code == 200:
        return r.json().get("messages", [])
    return []

def api_send_chat(msg: str, session_id: int | None):
    payload = {"message": msg}
    if session_id:
        payload["session_id"] = session_id
    r = st.session_state.http.post(f"{API}/chat", json=payload, timeout=60)
    return r.json(), r.status_code

def api_feedback(chat_id, fb):
    st.session_state.http.post(f"{API}/feedback", json={"chat_id": chat_id, "feedback": fb})

# UI
st.title("🩺 ICD Chatbot")

if not st.session_state.logged_in:
    left, right = st.columns(2)

    with left:
        st.subheader("Login")
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login", use_container_width=True):
            res, code = api_login(u, p)
            if code == 200:
                st.session_state.logged_in = True
                st.session_state.username = res.get("username", u)
                st.session_state.sessions_cache = res.get("sessions", [])
                st.session_state.active_session = res.get("latest_session_id")
                st.session_state.messages = [(m["role"], m["content"], m.get("chat_id")) for m in res.get("latest_messages", [])]
                st.success("Logged in!")
                st.rerun()
            else:
                st.error(res.get("error", "Login failed"))

    with right:
        st.subheader("Register")
        u2 = st.text_input("New username", key="reg_u")
        p2 = st.text_input("New password", type="password", key="reg_p")
        if st.button("Create account", use_container_width=True):
            res, code = api_register(u2, p2)
            if code == 200:
                st.success("Registered! Please login.")
            else:
                st.error(res.get("error", "Registration failed"))

else:
    # Sidebar
    with st.sidebar:
        st.write(f"👤 {st.session_state.username}")
        if st.button("➕ New Chat", use_container_width=True):
            sid = api_create_session("New Chat")
            if sid:
                st.session_state.sessions_cache = api_list_sessions()
                st.session_state.active_session = sid
                st.session_state.messages = []
                st.rerun()


        st.markdown("---")
        st.caption("Your chats")
        # defensive get
        for ses in st.session_state.sessions_cache:
            sid = ses.get("id")
            label = ses.get("title", f"Chat {sid}")
            if st.button(label, key=f"ses_{sid}", use_container_width=True):
                st.session_state.active_session = sid
                msgs = api_get_session_messages(sid)
                st.session_state.messages = [(m["role"], m["content"], m.get("chat_id")) for m in msgs]
                st.rerun()

        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            api_logout()
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.session_state.active_session = None
            st.session_state.sessions_cache = []
            st.rerun()

    # Main chat area
    chat_container = st.container()

    with chat_container:
        for role, content, chat_id in st.session_state.messages:
            with st.chat_message("user" if role == "user" else "assistant"):
                st.write(content)
                if role == "assistant" and chat_id:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("👍 Like", key=f"like_{chat_id}"):
                            api_feedback(chat_id, "liked")
                            st.toast("Feedback saved: 👍")
                    with c2:
                        if st.button("👎 Dislike", key=f"dislike_{chat_id}"):
                            api_feedback(chat_id, "disliked")
                            st.toast("Feedback saved: 👎")

    prompt = st.chat_input("Ask about an ICD code or title…")
    if prompt:
        if not st.session_state.active_session:
            sid = api_create_session("New Chat")
            if sid:
                st.session_state.active_session = sid
                st.session_state.sessions_cache = api_list_sessions()

        st.session_state.messages.append(("user", prompt, None))
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                data, code = api_send_chat(prompt, st.session_state.active_session)
                if code == 200 and "response" in data:
                    chat_id = data.get("chat_id")
                    response_text = data["response"]
                    st.session_state.messages.append(("assistant", response_text, chat_id))
                    st.write(response_text)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👍", key=f"like_inline_{chat_id}"):
                            api_feedback(chat_id, "liked")
                            st.success("You liked the response.")
                    with col2:
                        if st.button("👎", key=f"dislike_inline_{chat_id}"):
                            api_feedback(chat_id, "disliked")
                            st.error("You disliked the response.")

                    st.session_state.sessions_cache = api_list_sessions()
                else:
                    err = data.get("error", "Error")
                    st.session_state.messages.append(("assistant", err, None))
                    st.write(err)

        st.rerun()
