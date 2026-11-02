import uuid

import streamlit as st

from components import sidebar, chat_tab, voice_tab

st.set_page_config(page_title="PDF Chat Assistant", layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_pdfs" not in st.session_state:
    st.session_state.uploaded_pdfs = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "memory_enabled" not in st.session_state:
    st.session_state.memory_enabled = True

st.title("AI Voice & Chat PDF Assistant")

with st.sidebar:
    sidebar.show()

chat_col, voice_col = st.tabs(["Chat Q&A", "Voice Q&A"])

with chat_col:
    chat_tab.show()

with voice_col:
    voice_tab.show()
