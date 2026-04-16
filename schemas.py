from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    buyer_id: int
    store_id: Optional[int] = None
    store_name: str
    payment_method: str   # "toss" | "onsite"
    total_price: float
    items: List[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: str   # "pending" | "completed" | "cancelled"


class OrderItemResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: float
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_number: str
    buyer_id: int
    store_id: Optional[int] = None
    store_name: str
    status: str
    payment_method: str
    total_price: float
    created_at: datetime
    items: List[OrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)
