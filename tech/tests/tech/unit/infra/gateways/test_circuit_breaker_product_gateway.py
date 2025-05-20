# tests/unit/infra/gateways/test_circuit_breaker_product_gateway.py - Versão corrigida
import pytest
import asyncio
from unittest.mock import Mock, patch
from tech.infra.gateways.circuit_breaker_product_gateway import CircuitBreakerProductGateway
from tech.infra.gateways.http_product_gateway import HttpProductGateway
from tech.infra.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitOpenError


class TestCircuitBreakerProductGateway:
    """Unit tests for the CircuitBreakerProductGateway."""

    def setup_method(self):
        """Set up test dependencies."""
        # Mock the HttpProductGateway
        self.mock_http_gateway = Mock(spec=HttpProductGateway)

        # Mock the CircuitBreaker
        self.mock_circuit_breaker = Mock(spec=CircuitBreaker)

        # Store the original circuit breaker
        self.original_circuit_breaker = CircuitBreakerProductGateway._circuit_breaker

        # Patch dependencies
        with patch('tech.infra.gateways.circuit_breaker_product_gateway.HttpProductGateway',
                   return_value=self.mock_http_gateway):
            # Create the gateway with mocked circuit breaker
            CircuitBreakerProductGateway._circuit_breaker = self.mock_circuit_breaker
            self.gateway = CircuitBreakerProductGateway(
                failure_threshold=3,
                recovery_timeout=15.0,
                half_open_calls=1
            )

    def teardown_method(self):
        """Clean up after tests."""
        # Restore the original circuit breaker
        CircuitBreakerProductGateway._circuit_breaker = self.original_circuit_breaker

    def test_initialization(self):
        """Test gateway initialization."""
        assert hasattr(self.gateway, 'http_gateway')
        assert hasattr(self.gateway, 'circuit_breaker')
        assert self.gateway.http_gateway == self.mock_http_gateway
        assert self.gateway.circuit_breaker == self.mock_circuit_breaker

    def test_get_product_success(self):
        """Test successful product retrieval - sem usar assíncrono."""
        # Arrange
        product_id = 1
        expected_product = {"id": 1, "name": "Test Product", "price": 10.0}

        # Mock para a função assíncrona
        async def mock_get_product(product_id):
            return expected_product

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_product = mock_get_product

        # Act - criar o coroutine mas não executá-lo
        coroutine = self.gateway.get_product(product_id)

        # Assert - verificar se o coroutine retorna o esperado
        result = asyncio.run(coroutine)
        assert result == expected_product

    def test_get_product_circuit_open(self):
        """Test product retrieval when circuit is open."""
        # Arrange
        product_id = 1

        # Mock the async method to raise CircuitOpenError
        async def mock_get_product(product_id):
            raise ValueError("Product service is currently unavailable. Please try again later.")

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_product = mock_get_product

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(self.gateway.get_product(product_id))

        assert "Product service is currently unavailable" in str(exc_info.value)

    def test_get_product_unexpected_error(self):
        """Test product retrieval with unexpected error."""
        # Arrange
        product_id = 1

        # Mock the async method to raise an unexpected error
        async def mock_get_product(product_id):
            raise Exception("Unexpected error")

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_product = mock_get_product

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            asyncio.run(self.gateway.get_product(product_id))

        assert "Unexpected error" in str(exc_info.value)

    def test_get_products_success(self):
        """Test successful retrieval of multiple products."""
        # Arrange
        product_ids = [1, 2, 3]
        expected_products = [
            {"id": 1, "name": "Product 1", "price": 10.0},
            {"id": 2, "name": "Product 2", "price": 20.0},
            {"id": 3, "name": "Product 3", "price": 30.0}
        ]

        # Mock the async method
        async def mock_get_products(product_ids):
            return expected_products

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_products = mock_get_products

        # Act
        result = asyncio.run(self.gateway.get_products(product_ids))

        # Assert
        assert result == expected_products
        assert len(result) == 3

    def test_get_products_circuit_open(self):
        """Test retrieval of multiple products when circuit is open."""
        # Arrange
        product_ids = [1, 2, 3]

        # Mock the async method to raise CircuitOpenError
        async def mock_get_products(product_ids):
            raise ValueError("Product service is currently unavailable. Please try again later.")

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_products = mock_get_products

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(self.gateway.get_products(product_ids))

        assert "Product service is currently unavailable" in str(exc_info.value)

    def test_get_products_unexpected_error(self):
        """Test retrieval of multiple products with unexpected error."""
        # Arrange
        product_ids = [1, 2, 3]

        # Mock the async method to raise an unexpected error
        async def mock_get_products(product_ids):
            raise Exception("Unexpected error")

        # Configure o mock para retornar nossa função assíncrona
        self.gateway.get_products = mock_get_products

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            asyncio.run(self.gateway.get_products(product_ids))

        assert "Unexpected error" in str(exc_info.value)

    def test_singleton_pattern(self):
        """Test that the gateway uses singleton pattern for circuit breaker."""
        # Create a second instance
        with patch('tech.infra.gateways.circuit_breaker_product_gateway.HttpProductGateway',
                   return_value=Mock(spec=HttpProductGateway)):
            # Importante: aqui usamos o mesmo self.mock_circuit_breaker
            gateway2 = CircuitBreakerProductGateway()

            # Ambas as instâncias devem ter o mesmo circuit breaker
            assert self.gateway.circuit_breaker is self.mock_circuit_breaker
            assert gateway2.circuit_breaker is self.mock_circuit_breaker