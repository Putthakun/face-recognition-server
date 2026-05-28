import redis.asyncio as redis
from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    await get_redis().setex(key, ttl, value)


async def cache_get(key: str) -> str | None:
    return await get_redis().get(key)
