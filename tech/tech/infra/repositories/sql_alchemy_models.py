from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, create_engine
from sqlalchemy.orm import registry
from datetime import datetime
import enum

table_registry = registry()

class OrderStatus(enum.Enum):
    RECEIVED = 'RECEIVED'
    PREPARING = 'PREPARING'
    READY = 'READY'
    FINISHED = 'FINISHED'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'  # Adicionado este status
    PAID = 'PAID'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_ERROR = 'PAYMENT_ERROR'


@table_registry.mapped
class SQLAlchemyOrder(object):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    total_price = Column(Float, nullable=False)
    product_ids = Column(String,
                         nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.RECEIVED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_name = Column(String, nullable=True)
    user_email = Column(String, nullable=True)