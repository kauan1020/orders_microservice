# tests/tech/unit/infra/repositories/test_sql_alchemy_order_repository.py - Versão corrigida
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import select
from tech.domain.entities.orders import Order, OrderStatus
from tech.infra.repositories.sql_alchemy_order_repository import SQLAlchemyOrderRepository
from tech.infra.repositories.sql_alchemy_models import SQLAlchemyOrder


class TestSQLAlchemyOrderRepository:
    """Unit tests for the SQLAlchemyOrderRepository."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_session = Mock()
        self.repository = SQLAlchemyOrderRepository(self.mock_session)

        # Create a sample domain order
        self.domain_order = Order(
            id=1,
            total_price=100.0,
            product_ids="1,2,3",
            status=OrderStatus.RECEIVED
        )

        # Add user attributes
        setattr(self.domain_order, 'user_name', "Test User")
        setattr(self.domain_order, 'user_email', "test@example.com")

        # Create a sample SQLAlchemy model instance
        self.db_order = Mock(spec=SQLAlchemyOrder)
        self.db_order.id = 1
        self.db_order.total_price = 100.0
        self.db_order.product_ids = "1,2,3"
        self.db_order.status = OrderStatus.RECEIVED
        self.db_order.user_name = "Test User"
        self.db_order.user_email = "test@example.com"

    def test_to_domain_order(self):
        """Test conversion from SQLAlchemy model to domain entity."""
        # Act
        domain_order = self.repository._to_domain_order(self.db_order)

        # Assert
        assert isinstance(domain_order, Order)
        assert domain_order.id == self.db_order.id
        assert domain_order.total_price == self.db_order.total_price
        assert domain_order.product_ids == self.db_order.product_ids
        assert domain_order.status == self.db_order.status
        assert domain_order.user_name == self.db_order.user_name
        assert domain_order.user_email == self.db_order.user_email

    @patch('tech.infra.repositories.sql_alchemy_order_repository.SQLAlchemyOrder')
    def test_add_order(self, mock_model_class):
        """Test adding a new order to the database."""
        # Configure o mock para retornar nosso db_order
        mock_model_class.return_value = self.db_order

        # Act
        result = self.repository.add(self.domain_order)

        # Assert
        # Check that SQLAlchemyOrder was instantiated
        mock_model_class.assert_called_once()

        # Check repository operations
        self.mock_session.add.assert_called_once_with(self.db_order)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.db_order)

        # Check the result
        assert isinstance(result, Order)
        assert result.id == self.db_order.id
        assert result.total_price == self.db_order.total_price
        assert result.product_ids == self.db_order.product_ids
        assert result.status == self.db_order.status

    def test_get_by_id_found(self):
        """Test retrieving an order by ID when found."""
        # Arrange
        self.mock_session.scalar.return_value = self.db_order

        # Act
        result = self.repository.get_by_id(1)

        # Assert
        self.mock_session.scalar.assert_called_once()
        assert isinstance(result, Order)
        assert result.id == 1
        assert result.total_price == 100.0
        assert result.product_ids == "1,2,3"
        assert result.status == OrderStatus.RECEIVED

    def test_get_by_id_not_found(self):
        """Test retrieving an order by ID when not found."""
        # Arrange
        self.mock_session.scalar.return_value = None

        # Act
        result = self.repository.get_by_id(999)

        # Assert
        self.mock_session.scalar.assert_called_once()
        assert result is None

    def test_list_orders(self):
        """Test listing orders with pagination."""
        # Arrange
        db_orders = [self.db_order, Mock(spec=SQLAlchemyOrder)]
        db_orders[1].id = 2
        db_orders[1].total_price = 200.0
        db_orders[1].product_ids = "4,5"
        db_orders[1].status = OrderStatus.PREPARING

        # Mock the .all() result on the scalars query result
        scalar_result = Mock()
        scalar_result.all.return_value = db_orders
        self.mock_session.scalars.return_value = scalar_result

        # Act
        result = self.repository.list_orders(limit=10, skip=0)

        # Assert
        self.mock_session.scalars.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(order, Order) for order in result)
        assert result[0].id == 1
        assert result[1].id == 2

    def test_update_order_found(self):
        """Test updating an order when found."""
        # Arrange
        self.mock_session.scalar.return_value = self.db_order

        # Update the domain order
        updated_order = Order(
            id=1,
            total_price=150.0,  # Updated price
            product_ids="1,2,3,4",  # Updated products
            status=OrderStatus.PREPARING  # Updated status
        )
        setattr(updated_order, 'user_name', "Updated User")
        setattr(updated_order, 'user_email', "updated@example.com")

        # Act
        result = self.repository.update(updated_order)

        # Assert
        # Check the db_order was updated correctly
        assert self.db_order.total_price == 150.0
        assert self.db_order.product_ids == "1,2,3,4"
        assert self.db_order.status == OrderStatus.PREPARING
        assert self.db_order.user_name == "Updated User"
        assert self.db_order.user_email == "updated@example.com"

        # Check repository operations
        self.mock_session.scalar.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.db_order)

        # Check the result
        assert isinstance(result, Order)
        assert result.id == 1
        assert result.total_price == 150.0
        assert result.product_ids == "1,2,3,4"
        assert result.status == OrderStatus.PREPARING
        assert result.user_name == "Updated User"
        assert result.user_email == "updated@example.com"


    def test_delete_order_found(self):
        """Test deleting an order when found."""
        # Arrange
        self.mock_session.scalar.return_value = self.db_order

        # Act
        self.repository.delete(self.domain_order)

        # Assert
        self.mock_session.scalar.assert_called_once()
        self.mock_session.delete.assert_called_once_with(self.db_order)
        self.mock_session.commit.assert_called_once()

    def test_delete_order_not_found(self):
        """Test deleting an order when not found."""
        # Arrange
        self.mock_session.scalar.return_value = None

        # Act
        self.repository.delete(self.domain_order)

        # Assert
        self.mock_session.scalar.assert_called_once()
        self.mock_session.delete.assert_not_called()
        self.mock_session.commit.assert_not_called()