import streamlit as st
from api.client import upload_pdf


def show():
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")

    if uploaded_file and st.button("Process PDF"):
        with st.spinner("Processing PDF..."):
            data, error = upload_pdf(uploaded_file.getvalue(), uploaded_file.name, st.session_state.session_id)
            if data:
                st.success(data["message"])
                st.session_state.uploaded_pdfs.append(data["filename"])
            else:
                st.error(f"Error: {error}")

    if st.session_state.uploaded_pdfs:
        st.subheader("Uploaded PDFs")
        for pdf in st.session_state.uploaded_pdfs:
            st.text(f"- {pdf}")

    st.divider()

    st.session_state.memory_enabled = st.toggle(
        "Chat Memory",
        value=st.session_state.memory_enabled,
        help="ON: answers from all PDFs ever uploaded. OFF: answers only from PDFs uploaded in this session."
    )

    st.divider()

    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
