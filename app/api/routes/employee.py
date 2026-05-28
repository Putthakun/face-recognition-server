from fastapi import APIRouter

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/")
async def list_employees():
    pass


@router.post("/")
async def create_employee():
    pass
