import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
import os
import asyncio
from tech.infra.gateways.http_product_gateway import HttpProductGateway


def run_async(coroutine):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


class TestHttpProductGateway:
    """Unit tests for the HttpProductGateway."""

    def setup_method(self):
        """Set up test dependencies."""
        # Save original environment variable
        self.original_env = os.environ.get('SERVICE_PRODUCTS_URL')

        # Set environment variable for test
        os.environ['SERVICE_PRODUCTS_URL'] = 'http://test-products-service'

        # Create the gateway
        self.gateway = HttpProductGateway()

        # Sample products data
        self.products_data = [
            {"id": 1, "name": "Product 1", "price": 10.0, "category": "Category A"},
            {"id": 2, "name": "Product 2", "price": 20.0, "category": "Category B"},
            {"id": 3, "name": "Product 3", "price": 30.0, "category": "Category A"}
        ]

    def teardown_method(self):
        """Clean up after tests."""
        # Restore original environment variable
        if self.original_env:
            os.environ['SERVICE_PRODUCTS_URL'] = self.original_env
        else:
            del os.environ['SERVICE_PRODUCTS_URL']

    def test_initialization(self):
        """Test gateway initialization with environment variables."""
        assert self.gateway.base_url == 'http://test-products-service'
        assert self.gateway.timeout == 5.0

    def test_get_product_success(self):
        """Test successful product retrieval."""
        # Arrange
        product_id = 1

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Configurar mock_response.json para retornar um valor direto, não um coroutine
        mock_response.json = Mock(return_value=self.products_data)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act - Run the coroutine synchronously
            result = run_async(self.gateway.get_product(product_id))

        # Assert
        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/products/",
            timeout=self.gateway.timeout
        )
        assert result == self.products_data[0]

    def test_get_product_not_found(self):
        """Test product retrieval when product is not found."""
        # Arrange
        product_id = 999  # Non-existent ID

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Configurar mock_response.json para retornar um valor direto, não um coroutine
        mock_response.json = Mock(return_value=self.products_data)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                run_async(self.gateway.get_product(product_id))

        assert f"Product with ID {product_id} not found" in str(exc_info.value)

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/products/",
            timeout=self.gateway.timeout
        )

    def test_get_product_http_error(self):
        """Test product retrieval with HTTP error."""
        # Arrange
        product_id = 1

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        # Configure mock to raise HTTPStatusError
        mock_http_error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=mock_response
        )
        # Usar Mock em vez de AsyncMock para raise_for_status
        mock_response.raise_for_status = Mock(side_effect=mock_http_error)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                run_async(self.gateway.get_product(product_id))

        assert "Error fetching products" in str(exc_info.value)

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/products/",
            timeout=self.gateway.timeout
        )

    def test_get_products_success(self):
        """Test successful retrieval of multiple products."""
        # Arrange
        product_ids = [1, 2]

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Configurar mock_response.json para retornar um valor direto, não um coroutine
        mock_response.json = Mock(return_value=self.products_data)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act - Run the coroutine synchronously
            result = run_async(self.gateway.get_products(product_ids))

        # Assert
        mock_client.get.assert_called_once_with(f"{self.gateway.base_url}/products/")
        assert len(result) == 2
        assert result[0] == self.products_data[0]
        assert result[1] == self.products_data[1]

    def test_get_products_one_not_found(self):
        """Test retrieval of multiple products when one isn't found."""
        # Arrange
        product_ids = [1, 999]  # 999 doesn't exist

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Configurar mock_response.json para retornar um valor direto, não um coroutine
        mock_response.json = Mock(return_value=self.products_data)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                run_async(self.gateway.get_products(product_ids))

        assert "Product with ID 999 not found" in str(exc_info.value)

        mock_client.get.assert_called_once_with(f"{self.gateway.base_url}/products/")

    def test_get_products_connection_error(self):
        """Test retrieval of products with connection error."""
        # Arrange
        product_ids = [1, 2]

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()

        # Configure mock to raise ConnectError
        mock_connect_error = httpx.ConnectError("Failed to connect")
        mock_client.get.side_effect = mock_connect_error

        # Patch the AsyncClient
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                run_async(self.gateway.get_products(product_ids))

        assert "Cannot connect to products service" in str(exc_info.value)

        mock_client.get.assert_called_once_with(f"{self.gateway.base_url}/products/")