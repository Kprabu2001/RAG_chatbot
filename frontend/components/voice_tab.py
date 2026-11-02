import hashlib

import streamlit as st
from api.client import ask_voice
from utils.audio import autoplay_audio


def show():
    if "last_voice_hash" not in st.session_state:
        st.session_state.last_voice_hash = None

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("cached"):
                st.caption("Served from cache")

    audio_file = st.audio_input("Record a voice question", key="voice_recorder")

    if audio_file:
        audio_bytes = audio_file.getvalue()
        audio_hash = hashlib.md5(audio_bytes).hexdigest()

        # Streamlit reruns this code on every interaction, even on other tabs.
        # Without this guard, the same recording would be re-sent to the API
        # and its answer re-autoplayed on every rerun until a new recording
        # is made.
        if audio_hash != st.session_state.last_voice_hash:
            st.session_state.last_voice_hash = audio_hash

            with st.spinner("Processing voice..."):
                data, error = ask_voice(audio_bytes, st.session_state.session_id, st.session_state.memory_enabled)
                if data:
                    st.session_state.chat_history.append({"role": "user", "content": data["question"]})
                    with st.chat_message("user"):
                        st.markdown(data["question"])

                    with st.chat_message("assistant"):
                        st.markdown(data["answer"])
                        if data.get("cached"):
                            st.caption("Served from cache")
                        autoplay_audio(data["audio_base64"])
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": data["answer"],
                            "cached": data.get("cached", False),
                        })
                else:
                    st.error(f"Error: {error}")