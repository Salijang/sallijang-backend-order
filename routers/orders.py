from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime
import os
import httpx

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
NOTIFY_SERVICE_URL = os.getenv("NOTIFY_SERVICE_URL", "http://localhost:8003")


async def get_product_remaining(product_id: int) -> int | None:
    """Product Service에서 현재 재고를 조회합니다. 실패 시 None 반환."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{PRODUCT_SERVICE_URL}/api/v1/products/{product_id}",
                timeout=5.0,
            )
        if resp.status_code == 200:
            return resp.json().get("remaining")
        return None
    except Exception:
        return None


async def send_notify_event(event_type: str, order: models.Order) -> None:
    """Notify Service에 주문 이벤트를 전송합니다. 실패해도 주문 흐름에 영향 없음."""
    try:
        payload = {
            "event_type": event_type,
            "order_id": order.id,
            "order_number": order.order_number,
            "buyer_id": order.buyer_id,
            "store_id": order.store_id or 0,
            "store_name": order.store_name,
            "product_names": [item.product_name for item in order.items],
            "pickup_expected_at": order.pickup_expected_at,
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NOTIFY_SERVICE_URL}/api/v1/notifications/internal/order-event",
                json=payload,
                timeout=3.0,
            )
    except Exception as e:
        print(f"[WARNING] Notify Service 전송 실패 (event={event_type}, order_id={order.id}): {e}")


async def adjust_product_remaining(product_id: int, delta: int) -> tuple[bool, str]:
    """Product Service에 재고 수량 조정을 요청합니다. delta<0=감소, delta>0=복원.
    반환값: (성공 여부, 에러 메시지)"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{PRODUCT_SERVICE_URL}/api/v1/products/{product_id}/remaining",
                params={"delta": delta},
                timeout=5.0
            )
        if resp.status_code == 409:
            detail = resp.json().get("detail", "재고가 부족합니다.")
            return False, detail
        resp.raise_for_status()
        return True, ""
    except Exception as e:
        print(f"[WARNING] 재고 수량 조정 실패 (product_id={product_id}, delta={delta}): {e}")
        return False, "재고 서비스 연결에 실패했습니다."


def generate_order_number(order_id: int, created_at: datetime.datetime) -> str:
    date_str = created_at.strftime("%Y%m%d")
    return f"PK-{date_str}-{order_id:04d}"


@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    # pre-flight: 재고 사전 확인 (주문 생성 전에 빠르게 거부)
    for item_data in order_data.items:
        if item_data.product_id:
            remaining = await get_product_remaining(item_data.product_id)
            if remaining is None:
                raise HTTPException(
                    status_code=503,
                    detail="재고 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.",
                )
            if remaining < item_data.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"재고가 부족합니다. 현재 남은 수량: {remaining}개",
                )

    new_order = models.Order(
        order_number="TEMP",
        buyer_id=order_data.buyer_id,
        store_id=order_data.store_id,
        store_name=order_data.store_name,
        status="pending",
        payment_method=order_data.payment_method,
        total_price=order_data.total_price,
        pickup_expected_at=order_data.pickup_expected_at,
    )
    db.add(new_order)
    await db.flush()  # ID를 얻기 위해 flush (commit 전)

    new_order.order_number = generate_order_number(new_order.id, new_order.created_at)

    for item_data in order_data.items:
        item = models.OrderItem(
            order_id=new_order.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
        )
        db.add(item)

    # commit 전에 재고 차감 시도 — 재고 부족 시 DB 롤백 후 에러 반환
    deducted = []
    for item_data in order_data.items:
        if item_data.product_id:
            success, message = await adjust_product_remaining(item_data.product_id, -item_data.quantity)
            if not success:
                # 이미 차감한 항목 복원
                for restored_id, restored_qty in deducted:
                    await adjust_product_remaining(restored_id, restored_qty)
                await db.rollback()
                raise HTTPException(status_code=409, detail=message)
            deducted.append((item_data.product_id, item_data.quantity))

    await db.commit()

    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .filter(models.Order.id == new_order.id)
    )
    created_order = result.scalars().first()
    await send_notify_event("order_confirmed", created_order)
    return created_order


@router.get("/", response_model=List[schemas.OrderResponse])
async def list_orders(
    buyer_id: Optional[int] = None,
    store_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(models.Order).options(selectinload(models.Order.items))
    if buyer_id is not None:
        query = query.filter(models.Order.buyer_id == buyer_id)
    if store_id is not None:
        query = query.filter(models.Order.store_id == store_id)
    if status is not None:
        query = query.filter(models.Order.status == status)
    query = query.order_by(models.Order.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=schemas.OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status_update.status
    await db.commit()

    refreshed = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .filter(models.Order.id == order_id)
    )
    order = refreshed.scalars().first()

    if status_update.status == "completed":
        await send_notify_event("pickup_completed", order)
    elif status_update.status == "cancelled":
        await send_notify_event("order_cancelled", order)

    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    cancelled_by: str = Query(default="buyer", description="취소 주체: buyer | seller"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_snapshot = list(order.items)
    order.status = "cancelled"
    await db.commit()

    for item in items_snapshot:
        if item.product_id:
            await adjust_product_remaining(item.product_id, item.quantity)

    event_type = "order_cancelled_by_buyer" if cancelled_by == "buyer" else "order_cancelled_by_seller"
    await send_notify_event(event_type, order)
    return None
