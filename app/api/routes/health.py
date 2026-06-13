from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from app.services.face_service import face_service

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "face_db_count": len(face_service._face_db),
    }


@router.post("/api/reload")
async def reload_face_db():
    """Reload face vectors from Redis — call this after adding/removing employees."""
    await face_service.reload_face_db()
    return {
        "status": "reloaded",
        "face_db_count": len(face_service._face_db),
    }


@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
