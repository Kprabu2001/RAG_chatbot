import base64

import streamlit as st

AUDIO_MIME = "audio/mpeg"


def decode_audio(audio_base64: str) -> bytes:
    return base64.b64decode(audio_base64)


def play_audio(audio_bytes: bytes, autoplay: bool = False) -> None:
    st.audio(audio_bytes, format=AUDIO_MIME, autoplay=autoplay)
