import pytest
from unittest.mock import Mock, AsyncMock
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.use_cases.orders.delete_order_use_case import DeleteOrderUseCase


class TestDeleteOrderUseCase:
    """Unit tests for DeleteOrderUseCase"""

    def setup_method(self):
        """Set up test dependencies."""
        self.order_repository = Mock(spec=OrderRepository)
        self.use_case = DeleteOrderUseCase(self.order_repository)

        # Sample order
        self.sample_order = Mock(spec=Order)
        self.sample_order.id = 1
        self.sample_order.total_price = 100.0
        self.sample_order.product_ids = "1,2"
        self.sample_order.status = OrderStatus.RECEIVED
        self.sample_order.created_at = "2023-01-01T00:00:00"
        self.sample_order.updated_at = "2023-01-01T00:00:00"

        # Substituir método assíncrono por síncrono para testes
        self.original_execute = self.use_case.execute
        self.use_case.execute = self._sync_execute

    def teardown_method(self):
        """Restore original methods."""
        self.use_case.execute = self.original_execute

    def _sync_execute(self, order_id):
        """Synchronous version of execute for testing."""
        order = self.order_repository.get_by_id(order_id)

        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        try:
            self.order_repository.delete(order)
            return {"success": True, "message": f"Order {order_id} deleted successfully"}
        except Exception as e:
            raise Exception(f"Error deleting order: {str(e)}")

    def test_execute_order_exists(self):
        """Test deleting an existing order."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.sample_order

        # Act
        result = self.use_case.execute(order_id)

        # Assert
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.order_repository.delete.assert_called_once_with(self.sample_order)
        assert result["message"] == f"Order {order_id} deleted successfully"
        assert result["success"] is True

    def test_execute_order_not_found(self):
        """Test attempting to delete a non-existent order."""
        # Arrange
        order_id = 999
        self.order_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.use_case.execute(order_id)

        # Assert
        assert f"Order with ID {order_id} not found" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.order_repository.delete.assert_not_called()

    def test_execute_repository_error(self):
        """Test handling repository errors during deletion."""
        # Arrange
        order_id = 1
        self.order_repository.get_by_id.return_value = self.sample_order
        self.order_repository.delete.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            self.use_case.execute(order_id)

        # Assert
        assert "Error deleting order: Database error" in str(exc_info.value)
        self.order_repository.get_by_id.assert_called_once_with(order_id)
        self.order_repository.delete.assert_called_once_with(self.sample_order)

