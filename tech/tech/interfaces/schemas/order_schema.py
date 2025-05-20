from typing import Optional

from pydantic import BaseModel
from enum import Enum

class OrderStatusEnum(str, Enum):
    RECEIVED = 'RECEIVED'
    PREPARING = 'PREPARING'
    READY = 'READY'
    FINISHED = 'FINISHED'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'
    PAID = 'PAID'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_ERROR = 'PAYMENT_ERROR'


class OrderCreate(BaseModel):
    product_ids: list[int]
    cpf: Optional[str] = None


class OrderUpdate(BaseModel):
    status: OrderStatusEnum


class ProductDetail(BaseModel):
    id: int
    name: str
    price: float


class OrderPublic(BaseModel):
    id: int
    total_price: float
    status: OrderStatusEnum
    products: list[ProductDetail]
    user_info: Optional[dict] = None

    class Config:
        orm_mode = True


class OrderList(BaseModel):
    orders: list[OrderPublic]
