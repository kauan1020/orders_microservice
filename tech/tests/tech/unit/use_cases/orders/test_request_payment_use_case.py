# tests/unit/use_cases/orders/test_request_payment_use_case.py
import pytest
from unittest.mock import Mock
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.message_broker import MessageBroker
from tech.use_cases.orders.request_payment_use_case import RequestPaymentUseCase


class TestRequestPaymentUseCase:
    """Unit tests for the RequestPaymentUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.order_repository = Mock(spec=OrderRepository)
        self.message_broker = Mock(spec=MessageBroker)

        self.use_case = RequestPaymentUseCase(
            order_repository=self.order_repository,
            message_broker=self.message_broker
        )

        # Sample order
        self.order = Mock(spec=Order)
        self.order.id = 1
        self.order.total_price = 100.0
        self.order.product_ids = "1,2,3"
        self.order.status = OrderStatus.RECEIVED

        # Add user info
        setattr(self.order, 'user_name', "Test User")
        setattr(self.order, 'user_email', "test@example.com")
        setattr(self.order, 'user_cpf', "12345678901")

        # Updated order with new status
        self.updated_order = Mock(spec=Order)
        self.updated_order.id = 1
        self.updated_order.total_price = 100.0
        self.updated_order.product_ids = "1,2,3"
        self.updated_order.status = OrderStatus.AWAITING_PAYMENT
        setattr(self.updated_order, 'user_name', "Test User")
        setattr(self.updated_order, 'user_email', "test@example.com")
        setattr(self.updated_order, 'user_cpf', "12345678901")

    def test_request_payment_success(self):
        """Test successful payment request."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.order
        self.order_repository.update.return_value = self.updated_order

        # Expected message
        expected_message = {
            "order_id": 1,
            "amount": 100.0,
            "customer_info": {
                "name": "Test User",
                "email": "test@example.com",
                "cpf": "12345678901"
            }
        }

        # Act
        result = self.use_case.execute(order_id)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.message_broker.publish.assert_called_once_with(queue="payment_requests", message=expected_message)
        self.order_repository.update.assert_called_once()
        assert result.status == OrderStatus.AWAITING_PAYMENT

    def test_request_payment_order_not_found(self):
        """Test payment request for non-existent order."""
        # Arrange
        order_id = 999
        self.order_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.use_case.execute(order_id)

        assert f"Order with ID {order_id} not found" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.message_broker.publish.assert_not_called()
        self.order_repository.update.assert_not_called()

    def test_request_payment_message_broker_fails(self):
        """Test payment request when message broker fails."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.order
        self.message_broker.publish.side_effect = Exception("Failed to publish message")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.use_case.execute(order_id)

        assert "Erro ao publicar mensagem de pagamento" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.message_broker.publish.assert_called_once()
        self.order_repository.update.assert_not_called()

    def test_request_payment_without_user_info(self):
        """Test payment request for order without user information."""
        # Arrange
        order_id = 1

        # Create order without user info
        order_without_user = Mock(spec=Order)
        order_without_user.id = 1
        order_without_user.total_price = 100.0
        order_without_user.product_ids = "1,2,3"
        order_without_user.status = OrderStatus.RECEIVED
        # No user attributes

        # Updated order with new status
        updated_order_without_user = Mock(spec=Order)
        updated_order_without_user.id = 1
        updated_order_without_user.total_price = 100.0
        updated_order_without_user.product_ids = "1,2,3"
        updated_order_without_user.status = OrderStatus.AWAITING_PAYMENT
        # No user attributes

        self.order_repository.get_by_id.return_value = order_without_user
        self.order_repository.update.return_value = updated_order_without_user

        # Expected message with null user info
        expected_message = {
            "order_id": 1,
            "amount": 100.0,
            "customer_info": {
                "name": None,
                "email": None,
                "cpf": None
            }
        }

        # Act
        result = self.use_case.execute(order_id)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.message_broker.publish.assert_called_once_with(queue="payment_requests", message=expected_message)
        self.order_repository.update.assert_called_once()
        assert result.status == OrderStatus.AWAITING_PAYMENT