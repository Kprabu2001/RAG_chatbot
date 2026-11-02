import logging
import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.pdf.schemas.pdf_schemas import UploadResponse
from backend.pdf.services.cloudinary_service import CloudinaryService
from backend.rag.services.vector_service import VectorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/pdf", tags=["PDF"])
vector_service = VectorService()
cloudinary_service = CloudinaryService()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), session_id: str = Form("default")):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}_{file.filename}")

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        cloudinary_url = cloudinary_service.upload_pdf(file_path)
        filename, chunk_count = vector_service.ingest_pdf(file_path, cloudinary_url, session_id)
        return UploadResponse(
            filename=filename,
            message=f"PDF processed successfully into {chunk_count} chunks",
            chunk_count=chunk_count,
            cloudinary_url=cloudinary_url
        )
    except Exception as e:
        logger.exception("Failed to process PDF upload")
        raise HTTPException(500, f"Failed to process PDF: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
