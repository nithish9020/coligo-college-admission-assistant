"""High-performance Redis and in-memory dual cache service for Coligo."""

import json
import time
from typing import Any, Optional

import redis.asyncio as aioredis

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)

# Fallback in-memory cache: {key: (data_json_str, expire_timestamp)}
_LOCAL_MEMORY_CACHE: dict[str, tuple[str, float]] = {}
_MAX_LOCAL_ENTRIES = 1000

_redis_client: Optional[aioredis.Redis] = None
_redis_disabled = False


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Return a shared async Redis connection, or None if unreachable."""
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await client.ping()
        _redis_client = client
        logger.info("redis_connected_successfully", url=settings.REDIS_URL)
        return _redis_client
    except Exception as e:
        logger.warning(
            "redis_connection_failed_using_memory_fallback",
            url=settings.REDIS_URL,
            error=str(e),
        )
        _redis_disabled = True
        return None


async def get_cached_json(key: str) -> Optional[Any]:
    """Retrieve JSON-deserialized value from Redis or local memory fallback."""
    # 1. Try Redis
    redis_conn = await get_redis_client()
    if redis_conn is not None:
        try:
            val = await redis_conn.get(key)
            if val is not None:
                logger.debug("redis_cache_hit", key=key)
                return json.loads(val)
        except Exception as e:
            logger.warning("redis_get_error_falling_back", key=key, error=str(e))

    # 2. Try In-memory fallback
    now = time.time()
    if key in _LOCAL_MEMORY_CACHE:
        val_str, expires_at = _LOCAL_MEMORY_CACHE[key]
        if now < expires_at:
            logger.debug("memory_cache_hit", key=key)
            return json.loads(val_str)
        # Evict expired entry
        del _LOCAL_MEMORY_CACHE[key]

    return None


async def set_cached_json(
    key: str,
    value: Any,
    ttl_seconds: int = 86400,
) -> None:
    """Store JSON-serializable value in Redis and local memory fallback."""
    serialized = json.dumps(value)
    now = time.time()

    # 1. Store in In-memory fallback
    if len(_LOCAL_MEMORY_CACHE) >= _MAX_LOCAL_ENTRIES:
        # Evict oldest entry
        oldest_k = min(_LOCAL_MEMORY_CACHE, key=lambda k: _LOCAL_MEMORY_CACHE[k][1])
        del _LOCAL_MEMORY_CACHE[oldest_k]
    _LOCAL_MEMORY_CACHE[key] = (serialized, now + ttl_seconds)

    # 2. Store in Redis
    redis_conn = await get_redis_client()
    if redis_conn is not None:
        try:
            await redis_conn.set(key, serialized, ex=ttl_seconds)
            logger.debug("redis_cache_set", key=key, ttl=ttl_seconds)
        except Exception as e:
            logger.warning("redis_set_error", key=key, error=str(e))


def make_cutoff_cache_key(
    college: str,
    branch: str,
    community: str,
    round_no: int = 1,
) -> str:
    """Generate a deterministic cache key for college cutoff lookups."""
    clean_college = college.strip().lower()
    clean_branch = branch.strip().lower()
    clean_community = community.strip().upper()
    return f"coligo:cutoff:{clean_college}:{clean_branch}:{clean_community}:{round_no}"


def make_choice_filling_cache_key(
    cutoff: float,
    community: str,
    branches: tuple[str, ...],
    district: Optional[str] = None,
) -> str:
    """Generate a deterministic cache key for recommendation lists."""
    branches_str = ",".join(sorted(b.strip().lower() for b in branches))
    dist_str = (district or "all").strip().lower()
    return f"coligo:choices:{cutoff:.1f}:{community.upper()}:{branches_str}:{dist_str}"
