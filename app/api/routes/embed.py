from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import EmbedResponse
from app.services.face_service import face_service

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


@router.post("", response_model=EmbedResponse)
async def embed_face(file: UploadFile = File(..., description="Face image (jpg/png)")) -> EmbedResponse:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    embedding = await face_service.extract_embedding(image_bytes)

    if embedding is None:
        return EmbedResponse(face_detected=False)

    return EmbedResponse(face_detected=True, embedding=embedding.tolist())
