import struct
import numpy as np
import redis.asyncio as aioredis
import redis as syncredis

from app.core.config import settings

# ── Async client (used in async context) ──────────────────────────────────────
_async_client: aioredis.Redis | None = None


def get_async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.redis_url)
    return _async_client


# ── Sync client (used inside asyncio.to_thread) ───────────────────────────────
_sync_client: syncredis.Redis | None = None


def get_sync_redis() -> syncredis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = syncredis.from_url(settings.redis_url)
    return _sync_client


# ── Face vector helpers ────────────────────────────────────────────────────────

def _bytes_to_vector(data: bytes) -> np.ndarray:
    """Convert 4-bytes-per-float bytes back to numpy array."""
    n = len(data) // 4
    return np.array(struct.unpack(f"{n}f", data), dtype=np.float32)


def load_face_db_sync() -> dict[int, np.ndarray]:
    """
    Load all face vectors from Redis Hash into memory.
    Returns { emp_id (int) -> embedding (np.ndarray) }
    """
    client = get_sync_redis()
    entries = client.hgetall(settings.redis_hash_key)
    db: dict[int, np.ndarray] = {}
    for key, value in entries.items():
        emp_id = int(key)
        db[emp_id] = _bytes_to_vector(value)
    return db


async def load_face_db() -> dict[int, np.ndarray]:
    """Async version — load all face vectors from Redis."""
    client = get_async_redis()
    entries = await client.hgetall(settings.redis_hash_key)
    db: dict[int, np.ndarray] = {}
    for key, value in entries.items():
        emp_id = int(key)
        db[emp_id] = _bytes_to_vector(value)
    return db
