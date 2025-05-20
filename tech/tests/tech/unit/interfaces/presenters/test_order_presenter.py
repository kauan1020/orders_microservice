import pytest
from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.presenters.order_presenter import OrderPresenter
from unittest.mock import patch


class TestOrderPresenter:
    """Testes para o OrderPresenter, que formata respostas relacionadas a pedidos."""

    def setup_method(self):
        """Configuração inicial para os testes."""
        # Criar ordens de exemplo para usar nos testes
        self.sample_order = Order(
            total_price=100.0,
            product_ids="1,2,3",
            status=OrderStatus.RECEIVED
        )
        # Atribuir um ID para simular uma ordem salva
        self.sample_order.id = 1

        # Adicionar atributo 'products' para compatibilidade com o presenter
        setattr(self.sample_order, 'products', self.sample_order.product_ids)

        self.second_order = Order(
            total_price=200.0,
            product_ids="4,5",
            status=OrderStatus.PREPARING
        )
        self.second_order.id = 2

        # Adicionar atributo 'products' para compatibilidade com o presenter
        setattr(self.second_order, 'products', self.second_order.product_ids)

    def test_present_order(self):
        """Teste para o método present_order."""
        # Act
        result = OrderPresenter.present_order(self.sample_order)

        # Assert
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["total_price"] == 100.0
        assert result["status"] == OrderStatus.RECEIVED
        assert result["product_ids"] == self.sample_order.product_ids

    def test_present_order_list(self):
        """Teste para o método present_order_list."""
        # Arrange
        orders = [self.sample_order, self.second_order]

        # Act
        result = OrderPresenter.present_order_list(orders)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["total_price"] == 100.0
        assert result[0]["status"] == OrderStatus.RECEIVED
        assert result[0]["product_ids"] == self.sample_order.product_ids

        assert result[1]["id"] == 2
        assert result[1]["total_price"] == 200.0
        assert result[1]["status"] == OrderStatus.PREPARING
        assert result[1]["product_ids"] == self.second_order.product_ids

    def test_present_order_without_products(self):
        """Teste para o método present_order com uma ordem sem produtos."""
        # Arrange
        order_without_products = Order(
            total_price=50.0,
            product_ids="",
            status=OrderStatus.RECEIVED
        )
        order_without_products.id = 3

        # Adicionar atributo 'products' para compatibilidade com o presenter
        setattr(order_without_products, 'products', order_without_products.product_ids)

        # Act
        result = OrderPresenter.present_order(order_without_products)

        # Assert
        assert result["id"] == 3
        assert result["product_ids"] == order_without_products.product_ids
        assert result["total_price"] == 50.0
        assert result["status"] == OrderStatus.RECEIVED

    def test_present_order_with_additional_fields(self):
        """Teste para o método present_order com campos adicionais na ordem."""
        # Arrange
        order_with_user = self.sample_order
        order_with_user.user_name = "John Doe"
        order_with_user.user_email = "john@example.com"

        # Act
        result = OrderPresenter.present_order(order_with_user)

        # Assert
        assert result["id"] == 1
        assert result["total_price"] == 100.0
        assert result["status"] == OrderStatus.RECEIVED
        assert result["product_ids"] == order_with_user.product_ids
        # O presenter deve incluir apenas os campos definidos no método,
        # não enviando automaticamente campos extras
        assert "user_name" not in result
        assert "user_email" not in result