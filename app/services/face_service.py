import numpy as np
from app.core.config import settings


class FaceService:
    def __init__(self):
        self.threshold = settings.face_threshold

    async def encode_face(self, image_bytes: bytes) -> np.ndarray | None:
        raise NotImplementedError

    async def identify(self, encoding: np.ndarray) -> dict | None:
        raise NotImplementedError


face_service = FaceService()
