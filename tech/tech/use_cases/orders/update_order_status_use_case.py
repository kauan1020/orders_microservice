from tech.domain.entities.orders import OrderStatus
from tech.interfaces.schemas.order_schema import OrderStatusEnum, OrderPublic
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway


class UpdateOrderStatusUseCase:
    """
    Handles updating the status of an existing order.

    This use case allows changing the status of an order while maintaining its
    integrity. After updating the status, it retrieves full product details and
    user information to provide a complete response of the updated order.

    Attributes:
        order_repository: Repository interface for accessing and modifying order data.
        product_gateway: Gateway interface for retrieving product information.
        user_gateway: Gateway interface for retrieving user information.
    """

    def __init__(self, order_repository: OrderRepository, product_gateway: ProductGateway,
                 user_gateway: UserGateway = None):
        """
        Initialize the use case with necessary dependencies.

        Args:
            order_repository: Repository for order operations.
            product_gateway: Gateway for accessing product information.
            user_gateway: Optional gateway for accessing user information.
        """
        self.order_repository = order_repository
        self.product_gateway = product_gateway
        self.user_gateway = user_gateway

    async def execute(self, order_id: int, status: OrderStatusEnum) -> OrderPublic:
        """
        Updates an order's status and returns the complete updated order information.

        Retrieves the order, updates its status, and enriches the response with
        detailed product information from the product service. User information is
        preserved and included in the response when available.

        Args:
            order_id: The unique identifier of the order to update.
            status: The new status to assign to the order.

        Returns:
            An OrderPublic object containing the updated order with detailed
            product information, status, user data, and timestamps.

        Raises:
            ValueError: If the order with the given ID is not found.
        """
        new_status = OrderStatus(status.value)
        db_order = self.order_repository.get_by_id(order_id)

        if not db_order:
            raise ValueError("Order not found")

        db_order.status = new_status
        updated_order = self.order_repository.update(db_order)

        product_ids = list(map(int, updated_order.product_ids.split(','))) if updated_order.product_ids else []
        product_details = []

        if product_ids:
            try:
                products = await self.product_gateway.get_products(product_ids)
                product_details = [
                    {
                        "id": product["id"],
                        "name": product["name"],
                        "price": product["price"],
                    }
                    for product in products
                ]
            except ValueError as e:
                print(f"Error fetching product details: {str(e)}")
                product_details = [{"id": pid, "name": "Unknown", "price": 0} for pid in product_ids]

        order_response = OrderPublic(
            id=updated_order.id,
            total_price=updated_order.total_price,
            status=updated_order.status.value,
            products=product_details,
            created_at=updated_order.created_at,
            updated_at=updated_order.updated_at,
        )

        has_user_info = False
        user_info = {}

        if hasattr(updated_order, 'user_name') and updated_order.user_name is not None:
            user_info["name"] = updated_order.user_name
            has_user_info = True

        if hasattr(updated_order, 'user_email') and updated_order.user_email is not None:
            user_info["email"] = updated_order.user_email
            has_user_info = True

        if has_user_info:
            order_response.user_info = user_info

        return order_response