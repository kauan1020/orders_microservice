import pytest
from unittest.mock import Mock, patch, AsyncMock
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.interfaces.schemas.order_schema import OrderCreate
from tech.use_cases.orders.create_order_use_case import CreateOrderUseCase, create_use_case_with_resilience


class TestCreateOrderUseCase:
    """Tests for the CreateOrderUseCase using pytest-asyncio."""

    def setup_method(self):
        """Set up test dependencies."""
        self.order_repository = Mock(spec=OrderRepository)
        self.product_gateway = Mock(spec=ProductGateway)
        self.user_gateway = Mock(spec=UserGateway)

        self.use_case = CreateOrderUseCase(
            order_repository=self.order_repository,
            product_gateway=self.product_gateway,
            user_gateway=self.user_gateway
        )

        # Sample data
        self.product_data = [
            {"id": 1, "name": "Product 1", "price": 10.0},
            {"id": 2, "name": "Product 2", "price": 20.0},
            {"id": 3, "name": "Product 3", "price": 30.0}
        ]

        self.user_data = {
            "id": 1,
            "username": "test_user",
            "email": "user@example.com",
            "cpf": "12345678901"
        }

        self.mock_order = Mock(spec=Order)
        self.mock_order.id = 1
        self.mock_order.total_price = 60.0
        self.mock_order.status = OrderStatus.RECEIVED
        self.mock_order.created_at = "2023-01-01T00:00:00"
        self.mock_order.updated_at = "2023-01-01T00:00:00"

        # Setup async mocks
        self.product_gateway.get_products = AsyncMock(return_value=self.product_data)
        self.user_gateway.get_user_by_cpf = AsyncMock(return_value=self.user_data)
        self.order_repository.add.return_value = self.mock_order

    @pytest.mark.asyncio  # Use the pytest-asyncio marker
    async def test_execute_with_products_only(self):
        """Test creating an order with only products (no user info)."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf=None)

        # Act
        result = await self.use_case.execute(order_data)

        # Assert
        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])
        self.user_gateway.get_user_by_cpf.assert_not_called()

        # Verify the Order was created with correct data
        order_call = self.order_repository.add.call_args[0][0]
        assert order_call.total_price == 60.0
        assert order_call.product_ids == "1,2,3"
        assert order_call.status == OrderStatus.RECEIVED
        assert order_call.user_name is None
        assert order_call.user_email is None

        # Check the response
        assert result.id == 1
        assert result.total_price == 60.0
        assert result.status == OrderStatus.RECEIVED.value
        assert len(result.products) == 3
        assert not hasattr(result, "user_info") or result.user_info is None

    @pytest.mark.asyncio
    async def test_execute_with_user_info(self):
        """Test creating an order with user information."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf="12345678901")

        # Act
        result = await self.use_case.execute(order_data)

        # Assert
        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])
        self.user_gateway.get_user_by_cpf.assert_called_once_with("12345678901")

        # Verify the Order was created with correct data including user info
        order_call = self.order_repository.add.call_args[0][0]
        assert order_call.total_price == 60.0
        assert order_call.product_ids == "1,2,3"
        assert order_call.status == OrderStatus.RECEIVED
        assert order_call.user_name == "test_user"
        assert order_call.user_email == "user@example.com"

        # Check the response includes user info
        assert result.id == 1
        assert result.total_price == 60.0
        assert result.status == OrderStatus.RECEIVED.value
        assert len(result.products) == 3
        assert hasattr(result, "user_info")
        assert result.user_info["name"] == "test_user"
        assert result.user_info["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_execute_user_not_found(self):
        """Test creating an order when user is not found."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf="99999999999")
        self.user_gateway.get_user_by_cpf.return_value = None

        # Act
        result = await self.use_case.execute(order_data)

        # Assert
        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])
        self.user_gateway.get_user_by_cpf.assert_called_once_with("99999999999")

        # Verify the Order was created without user info
        order_call = self.order_repository.add.call_args[0][0]
        assert order_call.user_name is None
        assert order_call.user_email is None

        # Check the response doesn't include user info
        assert not hasattr(result, "user_info") or result.user_info is None

    @pytest.mark.asyncio
    async def test_execute_user_gateway_error(self):
        """Test creating an order when user gateway raises an error."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf="12345678901")
        self.user_gateway.get_user_by_cpf.side_effect = ValueError("User service unavailable")

        # Act
        result = await self.use_case.execute(order_data)

        # Assert
        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])
        self.user_gateway.get_user_by_cpf.assert_called_once_with("12345678901")

        # Verify the Order was created without user info
        order_call = self.order_repository.add.call_args[0][0]
        assert order_call.user_name is None
        assert order_call.user_email is None

        # Check the response doesn't include user info
        assert not hasattr(result, "user_info") or result.user_info is None

    @pytest.mark.asyncio
    async def test_execute_product_gateway_error(self):
        """Test handling of product gateway errors."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf=None)
        self.product_gateway.get_products.side_effect = ValueError("Product service unavailable")

        # Act & Assert
        with pytest.raises(ValueError, match="Product service unavailable"):
            await self.use_case.execute(order_data)

        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])
        self.user_gateway.get_user_by_cpf.assert_not_called()
        self.order_repository.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_empty_product_list(self):
        """Test creating an order when no products are returned from gateway."""
        # Arrange
        order_data = OrderCreate(product_ids=[1, 2, 3], cpf=None)
        self.product_gateway.get_products.return_value = []

        # Act
        result = await self.use_case.execute(order_data)

        # Assert
        self.product_gateway.get_products.assert_called_once_with([1, 2, 3])

        # Verify the Order was created with zero price
        order_call = self.order_repository.add.call_args[0][0]
        assert order_call.total_price == 0.0
        assert order_call.product_ids == "1,2,3"

        # Check the response has empty products list
        assert result.products == []

    @pytest.mark.asyncio
    @patch('tech.use_cases.orders.create_order_use_case.ProductGatewayFactory')
    @patch('tech.use_cases.orders.create_order_use_case.os.getenv')
    async def test_create_use_case_with_resilience(self, mock_getenv, mock_factory):
        """Test the creation of a use case with resilience settings."""
        # Arrange
        mock_order_repository = Mock(spec=OrderRepository)
        mock_user_gateway = Mock(spec=UserGateway)
        mock_product_gateway = Mock(spec=ProductGateway)
        mock_factory.create.return_value = mock_product_gateway

        # Setup the environment variable mocks
        def getenv_side_effect(name, default):
            env_values = {
                "CIRCUIT_BREAKER_THRESHOLD": "3",
                "CIRCUIT_BREAKER_TIMEOUT": "15.0",
                "CIRCUIT_BREAKER_HALF_OPEN": "2",
                "PRODUCT_GATEWAY_RESILIENCE": "circuit_breaker"
            }
            return env_values.get(name, default)

        mock_getenv.side_effect = getenv_side_effect

        # Act
        use_case = await create_use_case_with_resilience(mock_order_repository, mock_user_gateway)

        # Assert
        mock_factory.create.assert_called_once_with(
            resilience_mode="circuit_breaker",
            failure_threshold=3,
            recovery_timeout=15.0,
            half_open_calls=2
        )

        assert isinstance(use_case, CreateOrderUseCase)
        assert use_case.order_repository == mock_order_repository
        assert use_case.product_gateway == mock_product_gateway
        assert use_case.user_gateway == mock_user_gateway
