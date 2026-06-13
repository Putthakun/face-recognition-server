import asyncio
import base64
import logging
from datetime import datetime, timezone

import cv2
import httpx
import numpy as np
from insightface.app import FaceAnalysis

from app.core.config import settings
from app.models.schemas import RecognitionTask, RecognitionResult
from app.services.redis_service import load_face_db_sync, load_face_db

logger = logging.getLogger(__name__)


class FaceService:
    def __init__(self):
        self.threshold = settings.face_threshold
        self._model: FaceAnalysis | None = None
        self._face_db: dict[int, np.ndarray] = {}
        # per-employee cooldown (5 min): prevents same person re-entry
        self._last_seen: dict[str, datetime] = {}
        # per-camera cooldown (short): prevents blur→clear double-count for same person
        self._camera_last_tx: dict[int, datetime] = {}

    # ── Model ──────────────────────────────────────────────────────────────────

    def _load_model(self) -> FaceAnalysis:
        model = FaceAnalysis(
            name=settings.face_model_name,
            root=settings.face_model_dir,
            providers=["CPUExecutionProvider"] if settings.face_ctx_id < 0 else ["CUDAExecutionProvider"],
        )
        model.prepare(ctx_id=settings.face_ctx_id, det_size=(640, 640))
        return model

    @property
    def model(self) -> FaceAnalysis:
        if self._model is None:
            self._model = self._load_model()
            logger.info("InsightFace model '%s' loaded", settings.face_model_name)
        return self._model

    # ── Face DB (Redis) ────────────────────────────────────────────────────────

    def reload_face_db_sync(self) -> None:
        """Load face vectors from Redis (blocking — call on startup)."""
        self._face_db = load_face_db_sync()
        logger.info("Face DB loaded from Redis: %d employees", len(self._face_db))

    async def reload_face_db(self) -> None:
        """Reload face vectors from Redis (async)."""
        self._face_db = await load_face_db()
        logger.info("Face DB reloaded from Redis: %d employees", len(self._face_db))

    # ── Matching ───────────────────────────────────────────────────────────────

    def _match(self, embedding: np.ndarray) -> tuple[int | None, float]:
        if not self._face_db:
            return None, 0.0

        best_id, best_score = None, -1.0
        norm_q = embedding / (np.linalg.norm(embedding) + 1e-6)

        for emp_id, ref_emb in self._face_db.items():
            norm_r = ref_emb / (np.linalg.norm(ref_emb) + 1e-6)
            score = float(np.dot(norm_q, norm_r))
            if score > best_score:
                best_score, best_id = score, emp_id

        return best_id, best_score

    # ── Embedding extraction ───────────────────────────────────────────────────

    def _extract_embedding(self, image_bytes: bytes) -> np.ndarray | None:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        faces = self.model.get(img)
        if not faces:
            return None
        # use the largest face when multiple detected
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.embedding

    async def extract_embedding(self, image_bytes: bytes) -> np.ndarray | None:
        return await asyncio.to_thread(self._extract_embedding, image_bytes)

    # ── Recognition ───────────────────────────────────────────────────────────

    def _infer(self, image_bytes: bytes) -> tuple[int | None, float]:
        embedding = self._extract_embedding(image_bytes)
        if embedding is None:
            return None, 0.0
        return self._match(embedding)

    async def recognize(self, task: RecognitionTask) -> RecognitionResult:
        image_bytes = base64.b64decode(task.image_base64)
        emp_id, confidence = await asyncio.to_thread(self._infer, image_bytes)

        matched_id = emp_id if confidence >= self.threshold else None

        logger.info(
            "recognize → face_db=%d best_match=empId:%s score=%.4f threshold=%.2f → %s",
            len(self._face_db),
            emp_id,
            confidence,
            self.threshold,
            "MATCHED" if matched_id else "UNKNOWN",
        )

        return RecognitionResult(
            camera_id=task.camera_id,
            employee_id=matched_id,
            confidence=confidence,
        )

    # ── Cooldown ───────────────────────────────────────────────────────────────

    def _employee_key(self, result: RecognitionResult) -> str:
        return str(result.employee_id) if result.employee_id is not None else f"unknown_{result.camera_id}"

    def _is_in_cooldown(self, result: RecognitionResult) -> tuple[bool, str]:
        now = datetime.now(timezone.utc)

        # 1. Per-camera short cooldown — blocks blur→clear double-count
        cam_last = self._camera_last_tx.get(result.camera_id)
        if cam_last is not None:
            elapsed = (now - cam_last).total_seconds()
            if elapsed < settings.camera_cooldown_seconds:
                return True, f"camera cooldown ({elapsed:.1f}s / {settings.camera_cooldown_seconds}s)"

        # 2. Per-employee long cooldown — blocks same person re-entry
        emp_last = self._last_seen.get(self._employee_key(result))
        if emp_last is not None:
            elapsed = (now - emp_last).total_seconds()
            if elapsed < settings.transaction_cooldown_seconds:
                return True, f"employee cooldown ({elapsed:.0f}s / {settings.transaction_cooldown_seconds}s)"

        return False, ""

    def _mark_seen(self, result: RecognitionResult) -> None:
        now = datetime.now(timezone.utc)
        self._last_seen[self._employee_key(result)] = now
        self._camera_last_tx[result.camera_id] = now

    # ── Post transaction to .NET API ───────────────────────────────────────────

    async def post_transaction(self, result: RecognitionResult) -> None:
        in_cooldown, reason = self._is_in_cooldown(result)
        if in_cooldown:
            logger.debug("Skip transaction empId=%s camera=%d — %s", result.employee_id, result.camera_id, reason)
            return

        self._mark_seen(result)

        payload = {
            "empId":    result.employee_id,
            "cameraId": result.camera_id,
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.dotnet_api_url}/api/transactions",
                    json=payload,
                    timeout=5.0,
                )
                if res.status_code not in (200, 201):
                    logger.warning("Transaction POST failed: %s %s", res.status_code, res.text)
                else:
                    logger.info(
                        "Transaction saved: empId=%s cameraId=%s (cooldown=%ds)",
                        result.employee_id, result.camera_id,
                        settings.transaction_cooldown_seconds,
                    )
        except Exception as e:
            logger.error("Failed to post transaction: %s", e)


face_service = FaceService()
