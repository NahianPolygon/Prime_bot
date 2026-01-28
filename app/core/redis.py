import redis.asyncio as redis
from app.core.config import settings

redis_client = None


async def init_redis():
    global redis_client
    redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf8",
        decode_responses=True
    )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def get_redis():
    return redis_client

