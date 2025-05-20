from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class OrderStatus(str, Enum):
    RECEIVED = 'RECEIVED'
    PREPARING = 'PREPARING'
    READY = 'READY'
    FINISHED = 'FINISHED'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'  # Adicionado este status
    PAID = 'PAID'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_ERROR = 'PAYMENT_ERROR'


class Order:
    def __init__(self, total_price: float, product_ids: str, status: OrderStatus, id: Optional[int] = None,
                 user_name=None, user_email=None, user_cpf=None):
        self.id = id
        self.total_price = total_price
        self.product_ids = product_ids
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.user_name = user_name
        self.user_email = user_email
        self.user_cpf = user_cpf

    def dict(self) -> Dict[str, Any]:
        """
        Convert the Order entity to a dictionary.

        This method is used for JSON serialization and API responses.

        Returns:
            A dictionary representation of the Order.
        """
        result = {
            "id": self.id,
            "total_price": self.total_price,
            "product_ids": self.product_ids,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Add user information if available
        user_info = {}
        if self.user_name:
            user_info["name"] = self.user_name
        if self.user_email:
            user_info["email"] = self.user_email
        if self.user_cpf:
            user_info["cpf"] = self.user_cpf

        if user_info:
            result["user_info"] = user_info

        return result