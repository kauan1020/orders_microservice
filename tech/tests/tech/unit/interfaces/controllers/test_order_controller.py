import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.controllers.order_controller import OrderController
from tech.interfaces.schemas.order_schema import OrderCreate, OrderStatusEnum, OrderPublic


class TestOrderController:
    """Tests for the OrderController."""

    def setup_method(self):
        """Set up test dependencies."""
        # Create mocks for all use cases
        self.create_order_use_case = AsyncMock()
        self.list_orders_use_case = AsyncMock()
        self.update_order_status_use_case = AsyncMock()
        self.delete_order_use_case = AsyncMock()  # Alterado para AsyncMock

        # Create mocks for repository and gateway
        self.order_repository = Mock()
        self.product_gateway = AsyncMock()

        # Initialize the controller with mocks
        self.controller = OrderController(
            create_order_use_case=self.create_order_use_case,
            list_orders_use_case=self.list_orders_use_case,
            update_order_status_use_case=self.update_order_status_use_case,
            delete_order_use_case=self.delete_order_use_case
        )

        # Set repository and gateway for tests that need direct access
        self.controller.order_repository = self.order_repository
        self.controller.product_gateway = self.product_gateway

        # Mock order for testing
        self.mock_order = Mock(spec=Order)
        self.mock_order.id = 1
        self.mock_order.total_price = 100.0
        self.mock_order.product_ids = "1,2,3"
        self.mock_order.status = OrderStatus.RECEIVED
        setattr(self.mock_order, "user_name", "Test User")
        setattr(self.mock_order, "user_email", "test@example.com")

        # Sample products data
        self.products_data = [
            {"id": 1, "name": "Product 1", "price": 50.0},
            {"id": 2, "name": "Product 2", "price": 30.0},
            {"id": 3, "name": "Product 3", "price": 20.0}
        ]

        # Mock corretamente os métodos await
        self.mock_create_order_result = {
            "id": 1,
            "total_price": 100.0,
            "status": "RECEIVED",
            "products": [
                {"id": 1, "name": "Product 1", "price": 50.0},
                {"id": 2, "name": "Product 2", "price": 30.0},
                {"id": 3, "name": "Product 3", "price": 20.0}
            ],
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }

        self.mock_list_orders_result = [
            {
                "id": 1,
                "total_price": 100.0,
                "status": "RECEIVED",
                "products": [{"id": 1, "name": "Product 1", "price": 50.0}],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            },
            {
                "id": 2,
                "total_price": 200.0,
                "status": "PREPARING",
                "products": [{"id": 2, "name": "Product 2", "price": 200.0}],
                "created_at": "2023-01-02T00:00:00",
                "updated_at": "2023-01-02T00:00:00"
            }
        ]

        self.mock_update_order_result = {
            "id": 1,
            "total_price": 100.0,
            "status": "PREPARING",
            "products": [{"id": 1, "name": "Product 1", "price": 50.0}],
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }

    @pytest.mark.asyncio
    async def test_create_order_success(self):
        """Test successful order creation."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf="12345678901")

        # Configure o mock para retornar o objeto com método dict()
        mock_order = MagicMock()
        mock_order.dict.return_value = self.mock_create_order_result
        self.create_order_use_case.execute.return_value = mock_order

        # Act - Execute diretamente sem patch
        result = await self.controller.create_order(order_data)

        # Assert
        self.create_order_use_case.execute.assert_awaited_once_with(order_data)
        assert result == mock_order.dict.return_value
        assert result["id"] == 1
        assert result["total_price"] == 100.0
        assert result["status"] == "RECEIVED"
        assert len(result["products"]) == 3

    @pytest.mark.asyncio
    async def test_create_order_error(self):
        """Test order creation with error."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf="12345678901")
        self.create_order_use_case.execute.side_effect = ValueError("Product not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.controller.create_order(order_data)

        assert exc_info.value.status_code == 400
        assert "Product not found" in exc_info.value.detail
        self.create_order_use_case.execute.assert_awaited_once_with(order_data)

    @pytest.mark.asyncio
    async def test_list_orders(self):
        """Test listing orders."""
        # Arrange
        limit, skip = 10, 0

        # Criar objetos mock que tenham o método dict
        mock_order1 = MagicMock()
        mock_order1.dict.return_value = self.mock_list_orders_result[0]

        mock_order2 = MagicMock()
        mock_order2.dict.return_value = self.mock_list_orders_result[1]

        mock_orders = [mock_order1, mock_order2]
        self.list_orders_use_case.execute.return_value = mock_orders

        # Act - Execute diretamente sem patch
        result = await self.controller.list_orders(limit, skip)

        # Assert
        self.list_orders_use_case.execute.assert_awaited_once_with(limit, skip)
        assert len(result) == 2
        assert result[0] == mock_order1.dict.return_value
        assert result[1] == mock_order2.dict.return_value
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[0]["status"] == "RECEIVED"
        assert result[1]["status"] == "PREPARING"

    @pytest.mark.asyncio
    async def test_update_order_status(self):
        """Test updating order status."""
        # Arrange
        order_id = 1
        status = OrderStatusEnum.PREPARING

        # Usar MagicMock em vez de AsyncMock
        mock_order = MagicMock()
        mock_order.dict.return_value = self.mock_update_order_result

        self.update_order_status_use_case.execute.return_value = mock_order

        # Act - Execute diretamente sem patch
        result = await self.controller.update_order_status(order_id, status)

        # Assert
        self.update_order_status_use_case.execute.assert_awaited_once_with(order_id, status)
        assert result == mock_order.dict.return_value
        assert result["id"] == order_id
        assert result["status"] == "PREPARING"

    @pytest.mark.asyncio
    async def test_update_order_status_not_found(self):
        """Test updating status of non-existent order."""
        # Arrange
        order_id = 999
        status = OrderStatusEnum.PREPARING
        self.update_order_status_use_case.execute.side_effect = ValueError("Order not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.controller.update_order_status(order_id, status)

        assert exc_info.value.status_code == 404
        assert "Order not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_order_success(self):
        """Test successful order deletion."""
        # Arrange
        order_id = 1
        expected_response = {"message": f"Order {order_id} deleted successfully"}
        self.delete_order_use_case.execute.return_value = None

        # Act
        result = await self.controller.delete_order(order_id)

        # Assert
        self.delete_order_use_case.execute.assert_awaited_once_with(order_id)
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_delete_order_not_found(self):
        """Test order deletion with non-existent order."""
        # Arrange
        order_id = 999
        self.delete_order_use_case.execute.side_effect = ValueError("Order not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.controller.delete_order(order_id)

        assert exc_info.value.status_code == 404
        assert "Order not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_order_success(self):
        """Test successful order retrieval."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.mock_order
        self.product_gateway.get_products.return_value = self.products_data

        # Act
        result = await self.controller.get_order(order_id)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.product_gateway.get_products.assert_awaited_once()

        assert result["id"] == order_id
        assert result["total_price"] == 100.0
        assert result["status"] == "RECEIVED"
        assert len(result["products"]) == 3
        assert "user_info" in result
        assert result["user_info"]["name"] == "Test User"
        assert result["user_info"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_order_not_found(self):
        """Test order retrieval when order not found."""
        # Arrange
        order_id = 999
        self.order_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await self.controller.get_order(order_id)

        assert "Order with ID 999 not found" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)

    @pytest.mark.asyncio
    async def test_get_order_product_gateway_error(self):
        """Test order retrieval when product gateway fails."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.mock_order
        self.product_gateway.get_products.side_effect = ValueError("Product service unavailable")

        # Act
        result = await self.controller.get_order(order_id)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)

        # Verifica que o fallback para produtos desconhecidos funcionou
        assert result["id"] == order_id
        assert result["products"][0]["name"] == "Unknown"
        assert result["products"][0]["price"] == 0