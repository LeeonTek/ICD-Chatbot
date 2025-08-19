import streamlit as st
import requests

st.title("🩺 ICD Medical Chatbot")

BACKEND_URL = "http://127.0.0.1:5000/chat"

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

if prompt := st.chat_input("Ask about an ICD-10 code (e.g., A77.4, R45, J18)..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    BACKEND_URL,
                    json={"message": prompt, "history": st.session_state.messages},
                    timeout=60
                )
                response.raise_for_status()
                bot_reply = response.json().get("response", "⚠️ No response received.")
            except Exception as e:
                bot_reply = f"⚠️ Error: {str(e)}"

            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            # st.write(bot_reply)
            st.rerun()

    

