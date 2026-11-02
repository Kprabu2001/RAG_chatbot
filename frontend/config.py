import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def _resolve_api_url() -> str:
    url = os.getenv("BACKEND_URL") or _secret("BACKEND_URL")
    if not url:
        host = os.getenv("BACKEND_HOST") or _secret("BACKEND_HOST")
        if host:
            url = host if host.startswith(("http://", "https://")) else f"https://{host}"
    return (url or "http://localhost:8000").rstrip("/")


API_URL = _resolve_api_url()
