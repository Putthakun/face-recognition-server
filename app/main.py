import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import health, embed
from app.services.queue_service import start_consumer
from app.services.face_service import face_service

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load face vectors from Redis on startup
    face_service.reload_face_db_sync()

    # Start RabbitMQ consumer
    task = asyncio.create_task(start_consumer())
    logger.info("Face Recognition Server started")

    yield

    task.cancel()
    logger.info("Face Recognition Server stopped")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(health.router)
app.include_router(embed.router)
