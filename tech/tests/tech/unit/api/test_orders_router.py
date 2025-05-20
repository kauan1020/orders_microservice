import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tech.infra.databases.database import get_session
from tech.interfaces.gateways.order_gateway import OrderGateway
from tech.api.orders_router import router, get_order_controller, get_message_broker, handle_error, \
    get_request_payment_use_case
from tech.interfaces.schemas.order_schema import OrderCreate, OrderStatusEnum
from tech.use_cases.orders.request_payment_use_case import RequestPaymentUseCase

app = FastAPI()
app.include_router(router, prefix="/orders")


@pytest.fixture
def mock_session():
    """Mock da sessão SQLAlchemy."""
    return Mock(spec=Session)


@pytest.fixture
def mock_order_controller():
    """Mock do OrderController."""
    controller = Mock()
    controller.create_order = AsyncMock()
    controller.list_orders = AsyncMock()
    controller.update_order_status = AsyncMock()
    controller.delete_order = AsyncMock()
    controller.get_order = AsyncMock()
    return controller


@pytest.fixture
def mock_request_payment_use_case():
    """Mock do RequestPaymentUseCase."""
    use_case = Mock(spec=RequestPaymentUseCase)
    return use_case


@pytest.fixture
def client(mock_session, mock_order_controller, mock_request_payment_use_case):
    """Cliente de teste para as rotas FastAPI."""
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_order_controller] = lambda: mock_order_controller
    app.dependency_overrides[get_message_broker] = lambda: Mock()
    app.dependency_overrides[get_request_payment_use_case] = lambda: mock_request_payment_use_case
    return TestClient(app)


class TestOrderRoutes:
    """Testes para as rotas de pedidos."""

    def test_create_order_success(self, client, mock_order_controller):
        """Teste para criação de pedido com sucesso."""
        # Arrange
        order_data = {"product_ids": [1, 2, 3], "cpf": "12345678901"}
        expected_response = {
            "id": 1,
            "total_price": 150.0,
            "status": "RECEIVED",
            "products": [
                {"id": 1, "name": "Product 1", "price": 50.0},
                {"id": 2, "name": "Product 2", "price": 50.0},
                {"id": 3, "name": "Product 3", "price": 50.0}
            ]
        }
        mock_order_controller.create_order.return_value = expected_response

        # Act
        response = client.post("/orders/checkout", json=order_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == expected_response
        mock_order_controller.create_order.assert_called_once_with(OrderCreate(**order_data))

    def test_create_order_service_unavailable(self, client, mock_order_controller):
        """Teste para criação de pedido quando o serviço está indisponível."""
        # Arrange
        order_data = {"product_ids": [1, 2, 3], "cpf": "12345678901"}
        mock_order_controller.create_order.side_effect = ValueError("Product service is unavailable")

        # Act
        response = client.post("/orders/checkout", json=order_data)

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service temporarily unavailable" in response.json()["detail"]

    def test_list_orders_success(self, client, mock_order_controller):
        """Teste para listagem de pedidos com sucesso."""
        # Arrange
        expected_response = [
            {
                "id": 1,
                "total_price": 100.0,
                "status": "RECEIVED",
                "products": [{"id": 1, "name": "Product 1", "price": 50.0}]
            },
            {
                "id": 2,
                "total_price": 200.0,
                "status": "PREPARING",
                "products": [{"id": 2, "name": "Product 2", "price": 100.0}]
            }
        ]
        mock_order_controller.list_orders.return_value = expected_response

        # Act
        response = client.get("/orders/?limit=10&skip=0")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response
        mock_order_controller.list_orders.assert_called_once_with(10, 0)

    def test_update_order_status_success(self, client, mock_order_controller):
        """Teste para atualização de status de pedido com sucesso."""
        # Arrange
        expected_response = {
            "id": 1,
            "total_price": 100.0,
            "status": "PREPARING",
            "products": [{"id": 1, "name": "Product 1", "price": 50.0}]
        }
        mock_order_controller.update_order_status.return_value = expected_response

        # Act
        response = client.put("/orders/1?status=PREPARING")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response
        mock_order_controller.update_order_status.assert_called_once_with(1, OrderStatusEnum.PREPARING)

    def test_delete_order_success(self, client, mock_order_controller):
        """Teste para exclusão de pedido com sucesso."""
        # Arrange
        expected_response = {"message": "Order 1 deleted successfully"}
        mock_order_controller.delete_order.return_value = expected_response

        # Act
        response = client.delete("/orders/1")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response
        mock_order_controller.delete_order.assert_called_once_with(1)

    def test_get_order_success(self, client, mock_order_controller):
        """Teste para obtenção de pedido específico com sucesso."""
        # Arrange
        expected_response = {
            "id": 1,
            "total_price": 100.0,
            "status": "RECEIVED",
            "products": [{"id": 1, "name": "Product 1", "price": 50.0}]
        }
        mock_order_controller.get_order.return_value = expected_response

        # Act
        response = client.get("/orders/1")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response
        mock_order_controller.get_order.assert_called_once_with(1)

    def test_get_order_not_found(self, client, mock_order_controller):
        """Teste para obtenção de pedido inexistente."""
        # Arrange
        mock_order_controller.get_order.return_value = None

        # Act
        response = client.get("/orders/999")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Order 999 not found" in response.json()["detail"]
        mock_order_controller.get_order.assert_called_once_with(999)


class TestHandleError:
    """Testes para a função de tratamento de erros."""

    def test_service_unavailable(self):
        """Teste para erros de serviço indisponível."""
        error = ValueError("The product service is currently unavailable")
        exception = handle_error(error, "Test request")
        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service temporarily unavailable" in exception.detail

    def test_not_found(self):
        """Teste para erros de recurso não encontrado."""
        error = ValueError("Product with ID 999 not found")
        exception = handle_error(error, "Test request")
        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exception.detail

    def test_bad_request(self):
        """Teste para erros de requisição inválida."""
        error = ValueError("Invalid product ID format")
        exception = handle_error(error, "Test request")
        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid product ID format" in exception.detail

    def test_generic_error(self):
        """Teste para erros genéricos não categorizados."""
        error = Exception("Some unexpected error")
        exception = handle_error(error, "Test request")
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An unexpected error occurred" in exception.detail