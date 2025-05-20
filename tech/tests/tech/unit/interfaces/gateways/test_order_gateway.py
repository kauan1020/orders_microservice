import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from tech.domain.entities.orders import Order, OrderStatus
from tech.infra.repositories.sql_alchemy_order_repository import SQLAlchemyOrderRepository
from tech.interfaces.gateways.order_gateway import OrderGateway


class TestOrderGateway:
    """Testes para o OrderGateway, que adapta os use cases ao repositório."""

    def setup_method(self):
        """Configuração inicial para os testes."""
        self.mock_session = Mock(spec=Session)
        self.mock_repository = Mock(spec=SQLAlchemyOrderRepository)
        self.gateway = OrderGateway(self.mock_session)

        # Substituir o repositório real pelo mock
        self.gateway.repository = self.mock_repository

        # Criar uma ordem de exemplo para usar nos testes
        self.sample_order = Order(
            total_price=100.0,
            product_ids="1,2,3",
            status=OrderStatus.RECEIVED
        )

        # Atribuir um ID para simular uma ordem salva
        self.sample_order.id = 1

    def test_add_order(self):
        """Teste para o método add."""
        # Arrange
        self.mock_repository.add.return_value = self.sample_order

        # Act
        result = self.gateway.add(self.sample_order)

        # Assert
        self.mock_repository.add.assert_called_once_with(self.sample_order)
        assert result == self.sample_order
        assert result.id == 1
        assert result.total_price == 100.0
        assert result.status == OrderStatus.RECEIVED

    def test_get_by_id(self):
        """Teste para o método get_by_id."""
        # Arrange
        self.mock_repository.get_by_id.return_value = self.sample_order

        # Act
        result = self.gateway.get_by_id(1)

        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(1)
        assert result == self.sample_order
        assert result.id == 1

    def test_get_by_id_not_found(self):
        """Teste para o método get_by_id quando o pedido não é encontrado."""
        # Arrange
        self.mock_repository.get_by_id.return_value = None

        # Act
        result = self.gateway.get_by_id(999)

        # Assert
        self.mock_repository.get_by_id.assert_called_once_with(999)
        assert result is None

    def test_list_orders(self):
        """Teste para o método list_orders."""
        # Arrange
        orders = [self.sample_order,
                  Order(id=2, total_price=200.0, product_ids="4,5", status=OrderStatus.PREPARING)]
        self.mock_repository.list_orders.return_value = orders

        # Act
        result = self.gateway.list_orders(limit=10, skip=0)

        # Assert
        self.mock_repository.list_orders.assert_called_once_with(10, 0)
        assert result == orders
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

    def test_update(self):
        """Teste para o método update."""
        # Arrange
        updated_order = self.sample_order
        updated_order.status = OrderStatus.PREPARING
        self.mock_repository.update.return_value = updated_order

        # Act
        result = self.gateway.update(updated_order)

        # Assert
        self.mock_repository.update.assert_called_once_with(updated_order)
        assert result == updated_order
        assert result.status == OrderStatus.PREPARING

    def test_delete(self):
        """Teste para o método delete."""
        # Arrange - nothing special here

        # Act
        self.gateway.delete(self.sample_order)

        # Assert
        self.mock_repository.delete.assert_called_once_with(self.sample_order)