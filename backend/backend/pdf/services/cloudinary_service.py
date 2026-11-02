import os
import cloudinary
import cloudinary.uploader
from backend.base.config.settings import settings


class CloudinaryService:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

    def upload_pdf(self, file_path: str) -> str:
        result = cloudinary.uploader.upload(
            file_path,
            resource_type="raw",
            folder="pdf_chat_assistant"
        )
        return result["secure_url"]

    def delete_pdf(self, url: str) -> None:
        public_id = self._get_public_id(url)
        if public_id:
            cloudinary.uploader.destroy(public_id, resource_type="raw")

    def _get_public_id(self, url: str) -> str | None:
        parts = url.split("/")
        if "pdf_chat_assistant" in parts:
            idx = parts.index("pdf_chat_assistant")
            filename = parts[idx + 1] if idx + 1 < len(parts) else None
            if filename:
                return f"pdf_chat_assistant/{os.path.splitext(filename)[0]}"
        return None
