from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    message: str
    chunk_count: int
    cloudinary_url: str | None = None
