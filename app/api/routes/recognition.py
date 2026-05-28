from fastapi import APIRouter, Depends

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.post("/identify")
async def identify_face():
    pass
