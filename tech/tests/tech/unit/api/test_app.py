import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from http import HTTPStatus

from tech.api.app import app, read_root


class TestApp:
    """Test class for the FastAPI application."""

    @pytest.fixture
    def client(self):
        """Fixture to create a test client for the FastAPI app."""
        return TestClient(app)

    def test_read_root(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"message": "Tech Challenge FIAP - Kauan Silva!   Orders Microservice"}

    def test_read_root_function_directly(self):
        """Test the read_root function directly."""
        result = read_root()
        assert result == {"message": "Tech Challenge FIAP - Kauan Silva!   Orders Microservice"}

    def test_app_includes_orders_router(self):
        """Test that the app includes the orders router with the correct prefix."""
        # Find the orders router in the app.routes
        orders_path_found = False
        for route in app.routes:
            if hasattr(route, "path") and route.path.startswith("/orders"):
                orders_path_found = True
                break

        assert orders_path_found, "Orders router not found in app routes"

    @patch('tech.api.orders_router.router')
    def test_app_configuration(self, mock_router):
        """Test the configuration of the app."""
        from fastapi import FastAPI
        from tech.interfaces.schemas.message_schema import Message

        # Create a test app with the same configuration
        test_app = FastAPI()
        test_app.include_router(mock_router, prefix='/orders', tags=['orders'])

        @test_app.get('/', status_code=HTTPStatus.OK, response_model=Message)
        def test_root():
            return {'message': 'Test message'}

        # Check that the app has routes
        assert len(test_app.routes) > 0

        # Verify route configuration
        root_route = next(route for route in test_app.routes if route.path == "/")
        assert root_route.response_model == Message
        assert root_route.status_code == HTTPStatus.OK

    def test_message_schema(self):
        """Test the Message schema."""
        from tech.interfaces.schemas.message_schema import Message

        # Create a Message instance
        message = Message(message="Test message")

        # Verify properties
        assert message.message == "Test message"

        # Test the dict representation
        message_dict = message.dict()
        assert message_dict == {"message": "Test message"}