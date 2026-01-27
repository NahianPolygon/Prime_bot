import redis.asyncio as redis
from app.core.config import settings

redis_client = None


async def init_redis():
    """Initialize Redis client"""
    global redis_client
    redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf8",
        decode_responses=True
    )
    return redis_client


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis():
    """Get the Redis client"""
    return redis_client
