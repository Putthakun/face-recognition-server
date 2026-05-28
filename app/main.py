from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import recognition, employee, transaction, health

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health.router)
app.include_router(recognition.router, prefix="/api/v1")
app.include_router(employee.router, prefix="/api/v1")
app.include_router(transaction.router, prefix="/api/v1")
