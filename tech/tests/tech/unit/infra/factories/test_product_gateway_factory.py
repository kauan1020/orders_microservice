# tests/unit/infra/factories/test_product_gateway_factory.py - Versão corrigida
import pytest
from unittest.mock import patch, Mock
import os
from tech.infra.factories.product_gateway_factory import ProductGatewayFactory


class TestProductGatewayFactory:
    """Unit tests for the ProductGatewayFactory."""

    def test_create_with_none_resilience_mode(self, monkeypatch):
        """Test factory creating gateway with None resilience mode."""
        # Mock environment variable and imports
        monkeypatch.setenv("PRODUCT_GATEWAY_RESILIENCE", "circuit_breaker")

        # Use import patching for proper call interception
        circuit_breaker_mock = Mock()
        http_mock = Mock()

        # Criar instâncias reais para retornar dos mocks
        circuit_breaker_instance = Mock()
        http_instance = Mock()

        circuit_breaker_mock.return_value = circuit_breaker_instance
        http_mock.return_value = http_instance

        with patch.dict('sys.modules', {
            'tech.infra.gateways.circuit_breaker_product_gateway': Mock(
                CircuitBreakerProductGateway=circuit_breaker_mock),
            'tech.infra.gateways.http_product_gateway': Mock(HttpProductGateway=http_mock)
        }):
            # Reimportar o módulo após o patching
            with patch('tech.infra.factories.product_gateway_factory.CircuitBreakerProductGateway',
                       circuit_breaker_mock):
                # Act
                gateway = ProductGatewayFactory.create(resilience_mode=None)

                # Assert
                assert gateway is circuit_breaker_instance
                circuit_breaker_mock.assert_called_once()

    def test_create_with_circuit_breaker_resilience(self, monkeypatch):
        """Test factory creating gateway with 'circuit_breaker' resilience mode."""
        # Mock imports
        circuit_breaker_mock = Mock()
        circuit_breaker_instance = Mock()
        circuit_breaker_mock.return_value = circuit_breaker_instance

        with patch('tech.infra.factories.product_gateway_factory.CircuitBreakerProductGateway', circuit_breaker_mock):
            # Act
            gateway = ProductGatewayFactory.create(resilience_mode='circuit_breaker')

            # Assert
            assert gateway is circuit_breaker_instance
            circuit_breaker_mock.assert_called_once()
            # Verificar se os parâmetros padrão foram usados
            args, kwargs = circuit_breaker_mock.call_args
            assert kwargs['failure_threshold'] == 5
            assert kwargs['recovery_timeout'] == 30.0
            assert kwargs['half_open_calls'] == 1

    def test_create_with_none_resilience(self, monkeypatch):
        """Test factory creating gateway with 'none' resilience mode."""
        # Mock imports
        http_mock = Mock()
        http_instance = Mock()
        http_mock.return_value = http_instance

        with patch('tech.infra.factories.product_gateway_factory.HttpProductGateway', http_mock):
            # Act
            gateway = ProductGatewayFactory.create(resilience_mode='none')

            # Assert
            assert gateway is http_instance
            http_mock.assert_called_once()

    def test_create_with_custom_parameters(self, monkeypatch):
        """Test factory creating gateway with custom circuit breaker parameters."""
        # Mock imports
        circuit_breaker_mock = Mock()
        circuit_breaker_instance = Mock()
        circuit_breaker_mock.return_value = circuit_breaker_instance

        with patch('tech.infra.factories.product_gateway_factory.CircuitBreakerProductGateway', circuit_breaker_mock):
            # Act
            gateway = ProductGatewayFactory.create(
                resilience_mode='circuit_breaker',
                failure_threshold=10,
                recovery_timeout=60.0,
                half_open_calls=3
            )

            # Assert
            assert gateway is circuit_breaker_instance
            circuit_breaker_mock.assert_called_once()
            # Verificar se os parâmetros personalizados foram usados
            args, kwargs = circuit_breaker_mock.call_args
            assert kwargs['failure_threshold'] == 10
            assert kwargs['recovery_timeout'] == 60.0
            assert kwargs['half_open_calls'] == 3