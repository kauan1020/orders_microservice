import os
from tech.infra.factories.product_gateway_factory import ProductGatewayFactory
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.interfaces.schemas.order_schema import OrderCreate, OrderPublic


class CreateOrderUseCase:
    def __init__(self, order_repository: OrderRepository, product_gateway: ProductGateway, user_gateway: UserGateway):
        self.order_repository = order_repository
        self.product_gateway = product_gateway
        self.user_gateway = user_gateway

    async def execute(self, order_data: OrderCreate) -> OrderPublic:
        total_price = 0
        product_details = []
        user_info = None
        user_name = None
        user_email = None

        products = await self.product_gateway.get_products(order_data.product_ids)

        for product in products:
            total_price += product["price"]
            product_details.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
            })

        if order_data.cpf:
            try:
                user = await self.user_gateway.get_user_by_cpf(order_data.cpf)
                if user:
                    user_info = {
                        "name": user.get("username"),
                        "email": user.get("email")
                    }
                    user_name = user.get("username")
                    user_email = user.get("email")
            except ValueError as e:
                print(f"Error fetching user information: {str(e)}")

        order = Order(
            total_price=total_price,
            product_ids=','.join(map(str, order_data.product_ids)),
            status=OrderStatus.RECEIVED,
            user_name=user_name,
            user_email=user_email
        )

        saved_order = self.order_repository.add(order)

        response = OrderPublic(
            id=saved_order.id,
            total_price=saved_order.total_price,
            status=saved_order.status.value,
            products=product_details,
            created_at=saved_order.created_at,
            updated_at=saved_order.updated_at
        )

        if user_info:
            response.user_info = user_info

        return response


# Exemplo de uso com circuit breaker
async def create_use_case_with_resilience(order_repository: OrderRepository, user_gateway: UserGateway):
    # Configurações do circuit breaker
    failure_threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    recovery_timeout = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30.0"))
    half_open_calls = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN", "1"))

    # Obter o gateway de produtos com circuit breaker
    resilience_mode = os.getenv("PRODUCT_GATEWAY_RESILIENCE", "resilient")
    product_gateway = ProductGatewayFactory.create(
        resilience_mode=resilience_mode,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_calls=half_open_calls
    )

    # Criar o caso de uso com dependências
    return CreateOrderUseCase(
        order_repository=order_repository,
        product_gateway=product_gateway,
        user_gateway=user_gateway
    )