import streamlit as st
from api.client import ask_question


def show():
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("cached"):
                st.caption("Served from cache")

    if prompt := st.chat_input("Ask a question about your PDF"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                data, error = ask_question(prompt, st.session_state.session_id, st.session_state.memory_enabled)
                if data:
                    st.markdown(data["answer"])
                    if data.get("cached"):
                        st.caption("Served from cache")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data.get("sources", []),
                        "cached": data.get("cached", False),
                    })
                else:
                    st.error(f"Failed to get response: {error}")
