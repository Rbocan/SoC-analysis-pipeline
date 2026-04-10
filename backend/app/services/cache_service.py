"""Redis-based query caching."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis
import structlog

from app.settings import settings

logger = structlog.get_logger()

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _make_key(prefix: str, **kwargs) -> str:
    payload = json.dumps(kwargs, sort_keys=True, default=str)
    digest = hashlib.md5(payload.encode()).hexdigest()[:12]
    return f"soc:{prefix}:{digest}"


async def cache_get(key: str) -> Optional[Any]:
    try:
        val = await get_redis().get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning("Cache get error", key=key, error=str(e))
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    try:
        await get_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning("Cache set error", key=key, error=str(e))


async def cache_invalidate(pattern: str) -> None:
    try:
        redis = get_redis()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        logger.warning("Cache invalidate error", pattern=pattern, error=str(e))


def cached_query_key(product_id: str, **params) -> str:
    return _make_key("query", product_id=product_id, **params)
