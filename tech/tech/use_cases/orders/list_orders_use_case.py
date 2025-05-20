from tech.interfaces.schemas.order_schema import OrderPublic
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway


class ListOrdersUseCase:
    """
    Handles listing of orders with details including associated products and user information.

    This use case retrieves a paginated list of orders from the repository and
    enriches each order with detailed product information through the product gateway
    and user information through the user gateway when available.

    Attributes:
        order_repository: Repository interface for accessing order data.
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

    async def execute(self, limit: int, skip: int) -> list:
        """
        Retrieves a paginated list of orders with their complete details.

        Fetches orders from the repository and enriches each one with product details
        from the product service and user details from the user service when available.

        Args:
            limit: Maximum number of orders to retrieve.
            skip: Number of orders to skip for pagination.

        Returns:
            A list of OrderPublic objects containing enriched order information
            including products details, order status, user data, and timestamps.
        """
        orders = self.order_repository.list_orders(limit, skip)
        order_list = []

        for order in orders:
            print(f"Order ID: {order.id}")
            print(f"Has user_cpf attribute: {hasattr(order, 'user_cpf')}")
            if hasattr(order, 'user_cpf'):
                print(f"user_cpf value: {order.user_cpf}")
            print(f"Has user_name attribute: {hasattr(order, 'user_name')}")
            if hasattr(order, 'user_name'):
                print(f"user_name value: {order.user_name}")
            print(f"Has user_email attribute: {hasattr(order, 'user_email')}")
            if hasattr(order, 'user_email'):
                print(f"user_email value: {order.user_email}")

            product_ids = list(map(int, order.product_ids.split(','))) if order.product_ids else []

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
                id=order.id,
                total_price=order.total_price,
                status=order.status.value,
                products=product_details,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )

            has_user_info = False
            user_info = {}

            if hasattr(order, 'user_name') and order.user_name:
                user_info["name"] = order.user_name
                has_user_info = True

            if hasattr(order, 'user_email') and order.user_email:
                user_info["email"] = order.user_email
                has_user_info = True

            if has_user_info:
                order_response.user_info = user_info

            order_list.append(order_response)

        return order_list