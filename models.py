from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def kst_now() -> datetime:
    """현재 한국 표준시(KST, UTC+9)를 반환합니다."""
    return datetime.now(KST).replace(tzinfo=None)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {'schema': 'order_schema'}

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, index=True, nullable=False)
    # MSA 설계 원칙에 따라 논리적 참조만 사용합니다.
    store_id = Column(Integer, index=True, nullable=True)   # 장바구니 주문 시 null 허용
    store_name = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending | completed | cancelled
    payment_method = Column(String, nullable=False)              # toss | onsite
    total_price = Column(Float, nullable=False)
    pickup_expected_at = Column(String, nullable=True)  # 구매자 픽업 예정 시간 "HH:MM" 형식
    created_at = Column(DateTime, default=kst_now)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {'schema': 'order_schema'}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("order_schema.orders.id"), nullable=False)
    product_id = Column(Integer, index=True, nullable=True)  # 더미 상품은 null 허용
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
