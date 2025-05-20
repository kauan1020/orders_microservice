from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from tech.infra.databases.database import get_session
from tech.infra.factories.product_gateway_factory import ProductGatewayFactory
from tech.infra.factories.user_gateway_factory import UserGatewayFactory
from tech.interfaces.gateways.order_gateway import OrderGateway
from tech.interfaces.message_broker import MessageBroker
from tech.infra.rabbitmq_broker import RabbitMQBroker
from tech.interfaces.schemas.order_schema import OrderCreate, OrderStatusEnum
from tech.use_cases.orders.create_order_use_case import CreateOrderUseCase
from tech.use_cases.orders.list_orders_use_case import ListOrdersUseCase
from tech.use_cases.orders.request_payment_use_case import RequestPaymentUseCase
from tech.use_cases.orders.update_order_status_use_case import UpdateOrderStatusUseCase
from tech.use_cases.orders.delete_order_use_case import DeleteOrderUseCase
from tech.interfaces.controllers.order_controller import OrderController
import os
import logging
import re

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter()

SERVICE_UNAVAILABLE_PATTERN = re.compile(r'service is (currently )?(unavailable|down)|cannot connect|timed out',
                                         re.IGNORECASE)
NOT_FOUND_PATTERN = re.compile(r'not found|does not exist', re.IGNORECASE)
BAD_REQUEST_PATTERN = re.compile(r'invalid|required|missing|must be', re.IGNORECASE)


def get_message_broker() -> MessageBroker:
    """
    Provides a configured message broker instance for communication with queues.

    Creates and returns a RabbitMQ broker configured with environment variables.

    Returns:
        A configured MessageBroker implementation.
    """
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "user")
    password = os.getenv("RABBITMQ_PASS", "password")

    return RabbitMQBroker(host=host, port=port, user=user, password=password)


def get_request_payment_use_case(
        session: Session = Depends(get_session),
        message_broker: MessageBroker = Depends(get_message_broker)
) -> RequestPaymentUseCase:
    """
    Provides a configured RequestPaymentUseCase instance.

    Creates the use case with the necessary repository and message broker
    dependencies for processing payment requests.

    Args:
        session: SQLAlchemy database session.
        message_broker: Message broker for queue communication.

    Returns:
        Configured RequestPaymentUseCase instance.
    """
    order_repository = OrderGateway(session)
    return RequestPaymentUseCase(order_repository, message_broker)


def get_order_controller(session: Session = Depends(get_session)) -> OrderController:
    """
    Provides dependency injection for the OrderController with required gateways and repositories.

    This factory function creates all necessary dependencies for the OrderController,
    including data access gateways for orders, products, and users. It ensures proper
    separation of concerns by injecting these dependencies into the appropriate use cases.

    The function follows the Dependency Inversion Principle by providing concrete
    implementations of abstract interfaces at the composition root.

    Args:
        session: SQLAlchemy database session used for database operations.

    Returns:
        A fully configured OrderController instance with all required use cases
        and their dependencies properly initialized.
    """
    order_gateway = OrderGateway(session)

    failure_threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
    recovery_timeout = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "15.0"))
    half_open_calls = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN", "1"))

    product_gateway = ProductGatewayFactory.create(
        resilience_mode="circuit_breaker",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_calls=half_open_calls
    )

    user_gateway = UserGatewayFactory.create(
        resilience_mode="circuit_breaker",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_calls=half_open_calls
    )

    return OrderController(
        create_order_use_case=CreateOrderUseCase(order_gateway, product_gateway, user_gateway),
        list_orders_use_case=ListOrdersUseCase(order_gateway, product_gateway, user_gateway),
        update_order_status_use_case=UpdateOrderStatusUseCase(order_gateway, product_gateway, user_gateway),
        delete_order_use_case=DeleteOrderUseCase(order_gateway),
    )


def handle_error(e: Exception, request_info: str = "") -> HTTPException:
    """
    Analisa a exceção e retorna um HTTPException apropriado baseado no tipo de erro.

    Classifica os erros em diferentes categorias para fornecer status HTTP adequados:
    - 503 Service Unavailable: quando serviços externos estão indisponíveis
    - 404 Not Found: quando recursos não são encontrados
    - 400 Bad Request: para erros de validação e entradas inválidas
    - 500 Internal Server Error: para outros erros não categorizados

    Args:
        e: A exceção original
        request_info: Informações adicionais sobre a requisição para log

    Returns:
        HTTPException com status e mensagem apropriados
    """
    error_message = str(e)
    logger.error(f"Error processing request {request_info}: {error_message}")

    if SERVICE_UNAVAILABLE_PATTERN.search(error_message):
        logger.warning(f"Service unavailable detected: {error_message}")
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service temporarily unavailable: {error_message}"
        )
    elif NOT_FOUND_PATTERN.search(error_message):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_message
        )
    elif BAD_REQUEST_PATTERN.search(error_message) or isinstance(e, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    else:
        logger.error(f"Unhandled exception: {type(e).__name__}: {error_message}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {error_message}"
        )


@router.post("/checkout", status_code=201)
async def create_order(order: OrderCreate, request: Request,
                       controller: OrderController = Depends(get_order_controller)) -> dict:
    """
    Creates a new order with specified products and optional user identification.

    This endpoint processes order creation requests, validates the input data,
    communicates with the products service to obtain current pricing, and
    optionally retrieves user information if a CPF is provided.

    The endpoint returns a 201 Created status on success with complete order details
    including product information and optional user data.

    Args:
        order: Order creation data containing product IDs and optional CPF.
        controller: OrderController instance injected through dependencies.

    Returns:
        Complete order details including ID, status, product information, pricing,
        timestamps, and user information when available.

    Raises:
        HTTPException: With appropriate status code based on the type of error:
            - 400: When validation fails, products are not found, or other business rules are violated.
            - 404: When a specific resource is not found.
            - 503: When dependent services are unavailable.
            - 500: When unexpected server errors occur during processing.
    """
    try:
        logger.info(f"Creating order with {len(order.product_ids)} products")
        result = await controller.create_order(order)
        logger.info(f"Order created successfully with ID {result.get('id', 'unknown')}")
        return result
    except Exception as e:
        request_info = f"POST /checkout (products: {order.product_ids}, cpf: {order.cpf if order.cpf else 'none'})"
        raise handle_error(e, request_info)


@router.get("/")
async def list_orders(request: Request, limit: int = 10, skip: int = 0,
                     controller: OrderController = Depends(get_order_controller)) -> list:
    """
    Retrieves a paginated list of orders with complete details.

    This endpoint returns orders with their associated product information and user
    details when available. Results are paginated to ensure performance with large
    datasets.

    The endpoint communicates with the products service to enrich order data with
    current product information, including names and prices.

    Args:
        limit: Maximum number of orders to return in a single request.
        skip: Number of orders to skip for pagination purposes.
        controller: OrderController instance injected through dependencies.

    Returns:
        List of orders with complete details including products, status, pricing,
        timestamps, and user information when available.

    Raises:
        HTTPException: With appropriate status code based on the type of error
    """
    try:
        logger.info(f"Listing orders with limit={limit}, skip={skip}")
        result = await controller.list_orders(limit, skip)
        logger.info(f"Successfully retrieved {len(result)} orders")
        return result
    except Exception as e:
        request_info = f"GET / (limit: {limit}, skip: {skip})"
        raise handle_error(e, request_info)


@router.put("/{order_id}")
async def update_order_status(order_id: int, status: OrderStatusEnum, request: Request,
                              controller: OrderController = Depends(get_order_controller)) -> dict:
    """
    Updates the status of an existing order.

    This endpoint allows changing an order's status through its lifecycle.
    It first validates that the order exists, then updates its status,
    and returns the complete updated order information.

    The response includes current product details obtained from the products
    service and user information when available.

    Args:
        order_id: Unique identifier of the order to update.
        status: New status value to assign to the order.
        controller: OrderController instance injected through dependencies.

    Returns:
        Complete updated order details including status, product information,
        pricing, timestamps, and user information when available.

    Raises:
        HTTPException: With appropriate status code based on the type of error
    """
    try:
        logger.info(f"Updating order {order_id} status to {status}")
        result = await controller.update_order_status(order_id, status)
        logger.info(f"Order {order_id} status updated successfully to {status}")
        return result
    except Exception as e:
        request_info = f"PUT /{order_id} (status: {status})"
        raise handle_error(e, request_info)


@router.delete("/{order_id}")
async def delete_order(order_id: int, request: Request,
                       controller: OrderController = Depends(get_order_controller)) -> dict:
    """
    Permanently removes an order from the system.

    This endpoint finds and deletes the specified order. It performs validation
    to ensure the order exists before attempting deletion.

    Args:
        order_id: Unique identifier of the order to delete.
        controller: OrderController instance injected through dependencies.

    Returns:
        Success message confirming the order was deleted.

    Raises:
        HTTPException: With appropriate status code based on the type of error
    """
    try:
        logger.info(f"Deleting order {order_id}")
        result = await controller.delete_order(order_id)
        logger.info(f"Order {order_id} deleted successfully")
        return result
    except Exception as e:
        request_info = f"DELETE /{order_id}"
        raise handle_error(e, request_info)


@router.post("/{order_id}/request-payment")
async def request_payment(
        order_id: int,
        request: Request,
        request_payment_use_case: RequestPaymentUseCase = Depends(get_request_payment_use_case)
) -> dict:
    try:
        logger.info(f"Iniciando solicitação de pagamento para o pedido {order_id}")
        updated_order = request_payment_use_case.execute(order_id)
        logger.info(f"Pedido {order_id} atualizado com sucesso para status {updated_order.status.value}")

        return {
            "id": updated_order.id,
            "status": updated_order.status.value,
            "message": "Payment processing initiated",
            "total_price": updated_order.total_price
        }
    except Exception as e:
        request_info = f"POST /{order_id}/request-payment"
        raise handle_error(e, request_info)


@router.get("/{order_id}")
async def get_order(order_id: int, request: Request,
                    controller: OrderController = Depends(get_order_controller)) -> dict:
    """
    Retrieves details for a specific order.

    Args:
        order_id: Unique identifier of the order to retrieve.
        controller: OrderController instance injected through dependencies.

    Returns:
        Complete order details including products, status, and pricing.

    Raises:
        HTTPException: With appropriate status code based on the type of error
    """
    try:
        logger.info(f"Retrieving order {order_id}")
        order = await controller.get_order(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found")
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        logger.info(f"Order {order_id} retrieved successfully")
        return order
    except HTTPException as he:
        raise he
    except Exception as e:
        request_info = f"GET /{order_id}"
        raise handle_error(e, request_info)