import pytest
from unittest.mock import Mock, patch, AsyncMock
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.interfaces.schemas.order_schema import OrderStatusEnum
from tech.use_cases.orders.update_order_status_use_case import UpdateOrderStatusUseCase


class TestUpdateOrderStatusUseCase:
    """Unit tests for the UpdateOrderStatusUseCase using pytest-asyncio."""

    def setup_method(self):
        """Set up test dependencies."""
        self.order_repository = Mock(spec=OrderRepository)
        self.product_gateway = Mock(spec=ProductGateway)
        self.user_gateway = Mock(spec=UserGateway)

        self.use_case = UpdateOrderStatusUseCase(
            order_repository=self.order_repository,
            product_gateway=self.product_gateway,
            user_gateway=self.user_gateway
        )

        # Create a sample order
        self.sample_order = Mock(spec=Order)
        self.sample_order.id = 1
        self.sample_order.total_price = 100.0
        self.sample_order.product_ids = "1,2"
        self.sample_order.status = OrderStatus.RECEIVED
        self.sample_order.created_at = "2023-01-01T00:00:00"
        self.sample_order.updated_at = "2023-01-01T00:00:00"

        # Add user info to order
        setattr(self.sample_order, 'user_name', "Test User")
        setattr(self.sample_order, 'user_email', "test@example.com")

        # Sample products data
        self.products_data = [
            {"id": 1, "name": "Product 1", "price": 50.0},
            {"id": 2, "name": "Product 2", "price": 50.0}
        ]

        # Mock repository methods
        self.order_repository.get_by_id.return_value = self.sample_order
        self.order_repository.update.return_value = self.sample_order

        # Mock product gateway - make async for testing
        self.product_gateway.get_products = AsyncMock(return_value=self.products_data)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful order status update."""
        # Arrange
        order_id = 1
        new_status = OrderStatusEnum.PREPARING

        # Act
        result = await self.use_case.execute(order_id, new_status)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.order_repository.update.assert_called_once()

        # Verify status was updated
        updated_order = self.order_repository.update.call_args[0][0]
        assert updated_order.status.value == "PREPARING"

        # Verify products were fetched
        self.product_gateway.get_products.assert_called_once_with([1, 2])

        # Check response structure
        assert result.id == 1
        assert result.total_price == 100.0
        assert result.status == "PREPARING"
        assert len(result.products) == 2
        assert hasattr(result, "user_info")
        assert result.user_info["name"] == "Test User"
        assert result.user_info["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_execute_order_not_found(self):
        """Test updating status of non-existent order."""
        # Arrange
        order_id = 999
        new_status = OrderStatusEnum.PREPARING
        self.order_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await self.use_case.execute(order_id, new_status)

        assert "Order not found" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.order_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_product_gateway_error(self):
        """Test handling product gateway errors."""
        # Arrange
        order_id = 1
        new_status = OrderStatusEnum.PREPARING
        self.product_gateway.get_products.side_effect = ValueError("Product service unavailable")

        # Act
        result = await self.use_case.execute(order_id, new_status)

        # Assert
        self.order_repository.update.assert_called_once()
        assert result.id == 1
        assert result.status == "PREPARING"

        # Verify fallback product details were used - checking for both dict and object style access
        assert len(result.products) == 2
        product = result.products[0]

        # Try different ways to access the attributes based on the object type
        if hasattr(product, 'name'):
            # Object-style access
            assert product.name == "Unknown"
            assert product.price == 0
            assert product.id == 1
        else:
            # Dictionary-style access
            assert product["name"] == "Unknown"
            assert product["price"] == 0
            assert product["id"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_partial_user_info(self):
        """Test updating status with partial user info (only name, no email)."""
        # Arrange
        order_id = 1
        new_status = OrderStatusEnum.PREPARING

        # Setup partial user info
        partial_order = self.sample_order
        delattr(partial_order, 'user_email')
        self.order_repository.get_by_id.return_value = partial_order
        self.order_repository.update.return_value = partial_order

        # Act
        result = await self.use_case.execute(order_id, new_status)

        # Assert
        assert hasattr(result, "user_info")
        assert result.user_info["name"] == "Test User"
        assert "email" not in result.user_info

    @pytest.mark.asyncio
    async def test_execute_no_user_info(self):
        """Test updating status with no user info."""
        # Arrange
        order_id = 1
        new_status = OrderStatusEnum.PREPARING

        # Setup order with no user info
        no_user_order = Mock(spec=Order)
        no_user_order.id = 1
        no_user_order.total_price = 100.0
        no_user_order.product_ids = "1,2"
        no_user_order.status = OrderStatus.RECEIVED
        no_user_order.created_at = "2023-01-01T00:00:00"
        no_user_order.updated_at = "2023-01-01T00:00:00"

        self.order_repository.get_by_id.return_value = no_user_order
        self.order_repository.update.return_value = no_user_order

        # Act
        result = await self.use_case.execute(order_id, new_status)

        # Assert
        assert not hasattr(result, "user_info") or result.user_info is None

    @pytest.mark.asyncio
    async def test_execute_empty_product_ids(self):
        """Test updating status with no product IDs."""
        # Arrange
        order_id = 1
        new_status = OrderStatusEnum.PREPARING

        # Setup order with empty product_ids
        empty_products_order = Mock(spec=Order)
        empty_products_order.id = 1
        empty_products_order.total_price = 0.0
        empty_products_order.product_ids = ""
        empty_products_order.status = OrderStatus.RECEIVED
        empty_products_order.created_at = "2023-01-01T00:00:00"
        empty_products_order.updated_at = "2023-01-01T00:00:00"

        self.order_repository.get_by_id.return_value = empty_products_order
        self.order_repository.update.return_value = empty_products_order

        # Act
        result = await self.use_case.execute(order_id, new_status)

        # Assert
        self.product_gateway.get_products.assert_not_called()
        assert len(result.products) == 0