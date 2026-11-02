import base64
import streamlit as st


def autoplay_audio(audio_base64: str):
    audio_bytes = base64.b64decode(audio_base64)
    st.audio(audio_bytes, format="audio/wav", autoplay=True)
