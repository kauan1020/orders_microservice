import pytest
from unittest.mock import Mock, patch, AsyncMock
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.use_cases.orders.list_orders_use_case import ListOrdersUseCase


class TestListOrdersUseCase:
    """Unit tests for the ListOrdersUseCase using pytest-asyncio."""

    def setup_method(self):
        """Set up test dependencies."""
        self.order_repository = Mock(spec=OrderRepository)
        self.product_gateway = Mock(spec=ProductGateway)
        self.user_gateway = Mock(spec=UserGateway)

        self.use_case = ListOrdersUseCase(
            order_repository=self.order_repository,
            product_gateway=self.product_gateway,
            user_gateway=self.user_gateway
        )

        # Sample data
        self.orders = [
            Mock(spec=Order, id=1, total_price=100.0, product_ids="1,2", status=OrderStatus.RECEIVED,
                 created_at="2023-01-01T00:00:00", updated_at="2023-01-01T00:00:00"),
            Mock(spec=Order, id=2, total_price=200.0, product_ids="3,4", status=OrderStatus.PREPARING,
                 created_at="2023-01-02T00:00:00", updated_at="2023-01-02T00:00:00")
        ]

        # Add user info to first order
        setattr(self.orders[0], 'user_name', "User 1")
        setattr(self.orders[0], 'user_email', "user1@example.com")
        setattr(self.orders[0], 'user_cpf', "12345678901")

        self.products = [
            {"id": 1, "name": "Product 1", "price": 50.0},
            {"id": 2, "name": "Product 2", "price": 50.0},
            {"id": 3, "name": "Product 3", "price": 100.0},
            {"id": 4, "name": "Product 4", "price": 100.0}
        ]

        # Mock get_products to be async
        self.product_gateway.get_products = AsyncMock(return_value=self.products)

    @pytest.mark.asyncio
    async def test_execute_with_pagination(self):
        """Test listing orders with pagination."""
        # Arrange
        self.order_repository.list_orders.return_value = self.orders

        # Act
        result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        self.order_repository.list_orders.assert_called_once_with(10, 0)
        self.product_gateway.get_products.assert_called()
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].status == "RECEIVED"
        assert result[1].id == 2
        assert result[1].status == "PREPARING"

    @pytest.mark.asyncio
    async def test_execute_with_user_info(self):
        """Test listing orders that include user information."""
        # Arrange
        self.order_repository.list_orders.return_value = [self.orders[0]]

        # Act
        result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert hasattr(result[0], "user_info")
        assert result[0].user_info["name"] == "User 1"
        assert result[0].user_info["email"] == "user1@example.com"

    @pytest.mark.asyncio
    async def test_execute_empty_orders(self):
        """Test listing orders when no orders exist."""
        # Arrange
        self.order_repository.list_orders.return_value = []

        # Act
        result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        self.order_repository.list_orders.assert_called_once_with(10, 0)
        assert len(result) == 0
        self.product_gateway.get_products.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_product_gateway_error(self):
        """Test listing orders when product gateway fails."""
        # Arrange
        self.order_repository.list_orders.return_value = self.orders
        self.product_gateway.get_products.side_effect = ValueError("Product service unavailable")

        # Act
        result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        self.order_repository.list_orders.assert_called_once_with(10, 0)
        assert len(result) == 2

        # Check fallback product details - adjust for ProductDetail object
        assert len(result[0].products) > 0
        product = result[0].products[0]

        # Try different ways to access the name based on the object type
        if hasattr(product, 'name'):
            assert product.name == "Unknown"
            assert product.price == 0
        else:
            assert product["name"] == "Unknown"
            assert product["price"] == 0

    @pytest.mark.asyncio
    async def test_execute_empty_product_ids(self):
        """Test listing orders with empty product_ids."""
        # Arrange
        order_no_products = Mock(spec=Order, id=3, total_price=0.0, product_ids="",
                                 status=OrderStatus.RECEIVED,
                                 created_at="2023-01-03T00:00:00", updated_at="2023-01-03T00:00:00")
        self.order_repository.list_orders.return_value = [order_no_products]

        # Act
        result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        assert len(result) == 1
        assert result[0].id == 3
        assert len(result[0].products) == 0  # No products
        self.product_gateway.get_products.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_all_attributes_including_debug_print(self):
        """Test listing orders with all attributes including debug print statements"""
        # Arrange
        # Create a complete order with all possible attributes
        complete_order = Mock(spec=Order, id=5, total_price=300.0, product_ids="5,6",
                              status=OrderStatus.RECEIVED,
                              created_at="2023-01-05T00:00:00", updated_at="2023-01-05T00:00:00",
                              user_cpf="12345678901", user_name="Complete User", user_email="complete@example.com")

        self.order_repository.list_orders.return_value = [complete_order]

        more_products = [
            {"id": 5, "name": "Product 5", "price": 150.0},
            {"id": 6, "name": "Product 6", "price": 150.0}
        ]
        self.product_gateway.get_products.return_value = more_products

        # Act
        with patch('builtins.print') as mock_print:
            result = await self.use_case.execute(limit=10, skip=0)

        # Assert
        assert len(result) == 1
        assert result[0].id == 5
        assert len(result[0].products) == 2

        # Verify all attributes were processed correctly
        assert hasattr(result[0], "user_info")
        assert result[0].user_info["name"] == "Complete User"
        assert result[0].user_info["email"] == "complete@example.com"