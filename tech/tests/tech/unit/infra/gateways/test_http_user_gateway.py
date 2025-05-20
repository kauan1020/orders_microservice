import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
import os
import asyncio
from tech.infra.gateways.http_user_gateway import HttpUserGateway


class TestHttpUserGateway:
    """Unit tests for the HttpUserGateway."""

    def setup_method(self):
        """Set up test dependencies."""
        # Save original environment variable
        self.original_env = os.environ.get('SERVICE_USERS_URL')

        # Set environment variable for test
        os.environ['SERVICE_USERS_URL'] = 'http://test-users-service'

        # Create the gateway
        self.gateway = HttpUserGateway()

        # Sample user data
        self.user_data = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "cpf": "12345678901",
            "phone": "1234567890"
        }

    def teardown_method(self):
        """Clean up after tests."""
        # Restore original environment variable
        if self.original_env:
            os.environ['SERVICE_USERS_URL'] = self.original_env
        else:
            # Apenas remova se existir, evitando KeyError
            os.environ.pop('SERVICE_USERS_URL', None)

    def test_initialization(self):
        """Test gateway initialization with environment variables."""
        assert self.gateway.base_url == 'http://test-users-service'
        assert self.gateway.timeout == 5.0

    def test_initialization_default_values(self):
        """Test gateway initialization with default values."""
        # Remove environment variable to test default
        if 'SERVICE_USERS_URL' in os.environ:
            # Salvar para restaurar depois
            temp_val = os.environ['SERVICE_USERS_URL']
            os.environ.pop('SERVICE_USERS_URL', None)

        try:
            gateway = HttpUserGateway()
            assert gateway.base_url == 'http://localhost:8000'
            assert gateway.timeout == 5.0
        finally:
            # Restaurar para o valor do teste
            if 'temp_val' in locals():
                os.environ['SERVICE_USERS_URL'] = temp_val

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_success(self):
        """Test successful user retrieval by CPF."""
        # Arrange
        cpf = "12345678901"

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=self.user_data)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act - Run the coroutine
            result = await self.gateway.get_user_by_cpf(cpf)

        # Assert
        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )
        assert result == self.user_data

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_not_found(self):
        """Test user retrieval when user is not found."""
        # Arrange
        cpf = "99999999999"  # Non-existent CPF

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient to return our mock
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            result = await self.gateway.get_user_by_cpf(cpf)

        # Assert
        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_http_error(self):
        """Test user retrieval with HTTP error."""
        # Arrange
        cpf = "12345678901"

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
        mock_response.raise_for_status = Mock(side_effect=mock_http_error)
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch the AsyncClient
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await self.gateway.get_user_by_cpf(cpf)

        assert "Error fetching user with CPF" in str(exc_info.value)
        assert "500" in str(exc_info.value)

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_connection_error(self):
        """Test user retrieval with connection error."""
        # Arrange
        cpf = "12345678901"

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()

        # Configure mock to raise ConnectError
        mock_connect_error = httpx.ConnectError("Failed to connect")
        mock_client.get = AsyncMock(side_effect=mock_connect_error)

        # Patch the AsyncClient
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await self.gateway.get_user_by_cpf(cpf)

        assert "Cannot connect to users service" in str(exc_info.value)

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_timeout(self):
        """Test user retrieval with timeout."""
        # Arrange
        cpf = "12345678901"

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()

        # Configure mock to raise TimeoutException
        mock_timeout = httpx.TimeoutException("Request timed out")
        mock_client.get = AsyncMock(side_effect=mock_timeout)

        # Patch the AsyncClient
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await self.gateway.get_user_by_cpf(cpf)

        assert "Request to users service timed out" in str(exc_info.value)

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )

    @pytest.mark.asyncio
    async def test_get_user_by_cpf_unexpected_error(self):
        """Test user retrieval with unexpected error."""
        # Arrange
        cpf = "12345678901"

        # Mock the context manager for AsyncClient
        mock_client = AsyncMock()

        # Configure mock to raise general Exception
        mock_client.get = AsyncMock(side_effect=Exception("Unexpected error"))

        # Patch the AsyncClient and traceback
        with patch('httpx.AsyncClient') as mock_client_class, \
                patch('traceback.print_exc') as mock_traceback:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(ValueError) as exc_info:
                await self.gateway.get_user_by_cpf(cpf)

        assert "Failed to communicate with users service" in str(exc_info.value)
        mock_traceback.assert_called_once()

        mock_client.get.assert_called_once_with(
            f"{self.gateway.base_url}/users/cpf/{cpf}",
            timeout=self.gateway.timeout
        )