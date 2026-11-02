import requests
from config import API_URL

UPLOAD_TIMEOUT = 300
CHAT_TIMEOUT = 180


def _error_message(resp: requests.Response) -> str:
    try:
        payload = resp.json()
        detail = payload.get("detail") or payload.get("message")
        if detail:
            return str(detail)
    except ValueError:
        pass
    return resp.text or f"HTTP {resp.status_code}"


def _request_error(error: requests.exceptions.RequestException) -> str:
    response = getattr(error, "response", None)
    if response is not None:
        return _error_message(response)
    return str(error)


def upload_pdf(file_bytes, filename, session_id="default"):
    try:
        files = {"file": (filename, file_bytes, "application/pdf")}
        data = {"session_id": session_id}
        resp = requests.post(
            f"{API_URL}/v1/pdf/upload",
            files=files,
            data=data,
            timeout=UPLOAD_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, _request_error(e)


def ask_question(question, session_id="default", memory_enabled=True):
    try:
        resp = requests.post(
            f"{API_URL}/v1/chat/ask",
            json={"question": question, "session_id": session_id, "memory_enabled": memory_enabled},
            timeout=CHAT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, _request_error(e)


def ask_voice(audio_bytes, session_id="default", memory_enabled=True):
    try:
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {"session_id": session_id, "memory_enabled": str(memory_enabled).lower()}
        resp = requests.post(
            f"{API_URL}/v1/voice/chat",
            files=files,
            data=data,
            timeout=UPLOAD_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, _request_error(e)
