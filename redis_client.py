import os
import redis.asyncio as aioredis
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis


async def reserve_stock(product_id: int, quantity: int) -> Optional[bool]:
    """
    Redis에서 재고를 원자적으로 차감한다.
    반환값: True=성공, False=재고 부족, None=Redis 장애(폴백 필요)
    """
    try:
        r = await get_redis()
        key = f"remaining:{product_id}"
        new_val = await r.decrby(key, quantity)
        if new_val < 0:
            await r.incrby(key, quantity)  # 원복
            return False
        return True
    except Exception as e:
        print(f"[Redis] reserve_stock 실패 (product_id={product_id}): {e}")
        return None  # Redis 장애 → 폴백


async def restore_stock(product_id: int, quantity: int) -> None:
    """주문 취소 시 Redis 재고를 복원한다."""
    try:
        r = await get_redis()
        await r.incrby(f"remaining:{product_id}", quantity)
    except Exception as e:
        print(f"[Redis] restore_stock 실패 (product_id={product_id}): {e}")
