
import json
import os

import redis
from redis.exceptions import RedisError


REDIS_CACHE_URL = os.getenv(
    "REDIS_CACHE_URL",
    "redis://localhost:6379/1",
)

redis_cache = redis.Redis.from_url(
    REDIS_CACHE_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_cached_json(key: str):

    try:
        cached_value = redis_cache.get(key)
    except RedisError:
        return None

    if cached_value is None:
        return None

    try:
        return json.loads(cached_value)
    except (json.JSONDecodeError, TypeError):
        delete_cache_key(key)
        return None


def set_cached_json(
    key: str,
    value,
    ttl: int = 300,
) -> None:

    try:
        serialized_value = json.dumps(
            value,
            ensure_ascii=False,
        )
        redis_cache.set(key, serialized_value, ex=ttl)
    except (RedisError, TypeError, ValueError):
        pass


def delete_cache_key(key: str) -> None:

    try:
        redis_cache.delete(key)
    except RedisError:
        pass


def delete_cache_pattern(pattern: str) -> None:

    try:
        for key in redis_cache.scan_iter(match=pattern, count=100):
            redis_cache.delete(key)
    except RedisError:
        pass


def check_cache_connection() -> bool:

    try:
        return bool(redis_cache.ping())
    except RedisError:
        return False
