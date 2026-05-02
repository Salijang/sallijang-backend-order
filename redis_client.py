import os
import redis.asyncio as aioredis
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis = None

# 반환값: 1=성공, 0=재고 부족, 2=키 없음(cold start → HTTP 폴백)
_LUA_RESERVE = """
local exists = redis.call('EXISTS', KEYS[1])
if exists == 0 then return 2 end
local new = redis.call('DECRBY', KEYS[1], ARGV[1])
if new < 0 then
  redis.call('INCRBY', KEYS[1], ARGV[1])
  return 0
end
return 1
"""


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
    반환값: True=성공, False=재고 부족, None=키 없음 또는 Redis 장애(폴백 필요)
    """
    try:
        r = await get_redis()
        key = f"remaining:{product_id}"
        result = await r.eval(_LUA_RESERVE, 1, key, str(quantity))
        if result == 2:
            return None  # 키 없음(cold start) → HTTP 폴백
        if result == 0:
            return False  # 재고 부족
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
