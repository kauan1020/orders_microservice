import json
import pytest
from unittest.mock import MagicMock, patch, call
import pika
import requests
import os
import sys

# Importar o módulo a ser testado
# Assumindo que o código está em um arquivo chamado run_payment_response_worker.py
# Se o nome for diferente, ajuste conforme necessário
from tech.workers.run_payment_response_worker import  OrderUpdateService, callback, main
from tech.workers import run_payment_response_worker

class TestOrderUpdateService:
    """Testes para a classe OrderUpdateService."""

    def setup_method(self):
        """Configuração inicial para cada teste."""
        self.service = OrderUpdateService("http://test-order-service")

    def test_init(self):
        """Teste de inicialização do serviço."""
        assert self.service.order_service_url == "http://test-order-service"

    @pytest.mark.parametrize("payment_status,expected_order_status", [
        ("APPROVED", "PAID"),
        ("PENDING", "AWAITING_PAYMENT"),
        ("REJECTED", "PAYMENT_FAILED"),
        ("ERROR", "PAYMENT_ERROR"),
        ("UNKNOWN", None)
    ])
    def test_map_payment_status_to_order_status(self, payment_status, expected_order_status):
        """Teste do mapeamento de status de pagamento para status de pedido."""
        result = self.service._map_payment_status_to_order_status(payment_status)
        assert result == expected_order_status

    @patch("requests.put")
    def test_update_order_status_success(self, mock_put):
        """Teste de atualização de status com sucesso."""
        # Configurar o mock para retornar sucesso
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "status": "PAID"}
        mock_put.return_value = mock_response

        # Chamar o método
        result = self.service.update_order_status("123", "APPROVED")

        # Verificar chamada e resultado
        mock_put.assert_called_once_with(
            "http://test-order-service/123",
            params={"status": "PAID"},
            headers={"Content-Type": "application/json"}
        )
        assert result == {"success": True, "order": {"id": "123", "status": "PAID"}}

    @patch("requests.put")
    def test_update_order_status_invalid_payment_status(self, mock_put):
        """Teste com status de pagamento inválido."""
        result = self.service.update_order_status("123", "INVALID_STATUS")

        # Não deve chamar a API
        mock_put.assert_not_called()
        assert result == {
            "success": False,
            "message": "Status de pagamento não mapeado: INVALID_STATUS"
        }

    @patch("requests.put")
    def test_update_order_status_api_error(self, mock_put):
        """Teste de erro na API do serviço de pedidos."""
        # Configurar o mock para retornar erro
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_put.return_value = mock_response

        # Chamar o método
        result = self.service.update_order_status("123", "APPROVED")

        # Verificar chamada e resultado
        mock_put.assert_called_once()
        assert result == {
            "success": False,
            "status_code": 500,
            "message": "Internal Server Error"
        }

    @patch("requests.put")
    def test_update_order_status_connection_error(self, mock_put):
        """Teste de erro de conexão com a API."""
        # Configurar o mock para lançar exceção
        mock_put.side_effect = requests.RequestException("Connection error")

        # Chamar o método
        result = self.service.update_order_status("123", "APPROVED")

        # Verificar chamada e resultado
        mock_put.assert_called_once()
        assert result == {"success": False, "message": "Erro de conexão: Connection error"}

    @patch("requests.put")
    def test_update_order_status_general_exception(self, mock_put):
        """Teste de exceção genérica."""
        # Configurar o mock para lançar exceção
        mock_put.side_effect = Exception("Generic error")

        # Chamar o método
        result = self.service.update_order_status("123", "APPROVED")

        # Verificar chamada e resultado
        mock_put.assert_called_once()
        assert result == {"success": False, "message": "Erro: Generic error"}


class TestCallback:
    """Testes para a função de callback."""

    def setup_method(self):
        """Configuração inicial para cada teste."""
        self.channel = MagicMock()
        self.method = MagicMock()
        self.method.delivery_tag = "tag123"
        self.properties = MagicMock()
        self.order_service = MagicMock()

    def test_callback_success(self):
        """Teste de callback com sucesso."""
        # Preparar mensagem de teste
        message = {
            "order_id": "123",
            "status": "APPROVED"
        }
        body = json.dumps(message).encode()

        # Configurar mock de order_service
        self.order_service.update_order_status.return_value = {"success": True}

        # Chamar callback
        callback(self.channel, self.method, self.properties, body, self.order_service)

        # Verificar chamadas
        self.order_service.update_order_status.assert_called_once_with("123", "APPROVED")
        self.channel.basic_ack.assert_called_once_with(delivery_tag="tag123")

    def test_callback_invalid_json(self):
        """Teste com JSON inválido."""
        # Preparar mensagem inválida
        body = b"invalid json"

        # Chamar callback
        callback(self.channel, self.method, self.properties, body, self.order_service)

        # Verificar chamadas
        self.order_service.update_order_status.assert_not_called()
        self.channel.basic_ack.assert_called_once_with(delivery_tag="tag123")

    def test_callback_missing_fields(self):
        """Teste com campos obrigatórios ausentes."""
        # Preparar mensagem incompleta
        message = {"some_field": "value"}
        body = json.dumps(message).encode()

        # Chamar callback
        callback(self.channel, self.method, self.properties, body, self.order_service)

        # Verificar chamadas
        self.order_service.update_order_status.assert_not_called()
        self.channel.basic_ack.assert_called_once_with(delivery_tag="tag123")

    def test_callback_exception(self):
        """Teste com exceção durante processamento."""
        # Preparar mensagem de teste
        message = {
            "order_id": "123",
            "status": "APPROVED"
        }
        body = json.dumps(message).encode()

        # Configurar mock para lançar exceção
        self.order_service.update_order_status.side_effect = Exception("Processing error")

        # Chamar callback
        callback(self.channel, self.method, self.properties, body, self.order_service)

        # Verificar chamadas
        self.order_service.update_order_status.assert_called_once()
        self.channel.basic_nack.assert_called_once_with(delivery_tag="tag123", requeue=False)


# Testes para cobertura completa
def test_module_variables():
    """Teste das variáveis de módulo."""
    # Verificar valores padrão
    assert run_payment_response_worker.RABBITMQ_HOST == "localhost"
    assert run_payment_response_worker.RABBITMQ_PORT == 5672
    assert run_payment_response_worker.RABBITMQ_USER == "user"
    assert run_payment_response_worker.RABBITMQ_PASS == "password"
    assert run_payment_response_worker.ORDER_SERVICE_URL == "http://localhost:8003"
    assert run_payment_response_worker.PAYMENT_RESPONSES_QUEUE == "payment_responses"

    # Verificar valores com variáveis de ambiente
    original_env = os.environ.copy()

    os.environ["RABBITMQ_HOST"] = "custom-host"
    os.environ["RABBITMQ_PORT"] = "1234"
    os.environ["RABBITMQ_USER"] = "custom-user"
    os.environ["RABBITMQ_PASS"] = "custom-pass"
    os.environ["SERVICE_ORDERS_URL"] = "http://custom-url"

    # Recarregar o módulo para aplicar as novas variáveis de ambiente
    import importlib
    importlib.reload(run_payment_response_worker)

    # Verificar valores atualizados
    assert run_payment_response_worker.RABBITMQ_HOST == "custom-host"
    assert run_payment_response_worker.RABBITMQ_PORT == 1234
    assert run_payment_response_worker.RABBITMQ_USER == "custom-user"
    assert run_payment_response_worker.RABBITMQ_PASS == "custom-pass"
    assert run_payment_response_worker.ORDER_SERVICE_URL == "http://custom-url"

    # Restaurar variáveis de ambiente
    os.environ.clear()
    os.environ.update(original_env)
    importlib.reload(run_payment_response_worker)


if __name__ == "__main__":
    pytest.main(["-v"])