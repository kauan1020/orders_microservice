import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio
from typing import Dict, Any, Callable
from tech.interfaces.message_broker import MessageBroker


class TestableMessageBroker(MessageBroker):
    def __init__(self):
        self.messages = {}
        self.is_connected = True

    def publish(self, queue: str, message: Dict[str, Any]) -> None:
        if not self.is_connected:
            raise ConnectionError("Broker not connected")

        if queue not in self.messages:
            self.messages[queue] = []
        self.messages[queue].append(message)

    def consume(self, queue: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        if not self.is_connected:
            raise ConnectionError("Broker not connected")

        if queue in self.messages:
            for message in self.messages[queue]:
                callback(message)

    def close(self) -> None:
        self.is_connected = False

    async def publish_async(self, queue: str, message: Dict[str, Any]) -> None:
        await asyncio.sleep(0.01)
        self.publish(queue, message)


class TestMessageBroker:
    """Testes para a interface MessageBroker."""

    def setup_method(self):
        """Configuração para cada teste."""
        self.broker = TestableMessageBroker()

    def test_publish(self):
        """Teste de publicação de mensagem."""
        # Arrange
        queue = "test_queue"
        message = {"id": 1, "action": "test"}

        # Act
        self.broker.publish(queue, message)

        # Assert
        assert queue in self.broker.messages
        assert message in self.broker.messages[queue]
        assert len(self.broker.messages[queue]) == 1

    def test_publish_multiple(self):
        """Teste de publicação de múltiplas mensagens."""
        # Arrange
        queue = "test_queue"
        message1 = {"id": 1, "action": "test1"}
        message2 = {"id": 2, "action": "test2"}

        # Act
        self.broker.publish(queue, message1)
        self.broker.publish(queue, message2)

        # Assert
        assert len(self.broker.messages[queue]) == 2
        assert message1 in self.broker.messages[queue]
        assert message2 in self.broker.messages[queue]

    def test_publish_to_multiple_queues(self):
        """Teste de publicação em múltiplas filas."""
        # Arrange
        queue1 = "queue1"
        queue2 = "queue2"
        message1 = {"id": 1, "queue": "queue1"}
        message2 = {"id": 2, "queue": "queue2"}

        # Act
        self.broker.publish(queue1, message1)
        self.broker.publish(queue2, message2)

        # Assert
        assert queue1 in self.broker.messages
        assert queue2 in self.broker.messages
        assert message1 in self.broker.messages[queue1]
        assert message2 in self.broker.messages[queue2]

    def test_publish_after_close(self):
        """Teste de publicação após fechamento da conexão."""
        # Arrange
        queue = "test_queue"
        message = {"id": 1, "action": "test"}
        self.broker.close()

        # Act & Assert
        with pytest.raises(ConnectionError):
            self.broker.publish(queue, message)

    def test_consume(self):
        """Teste de consumo de mensagens."""
        # Arrange
        queue = "test_queue"
        message1 = {"id": 1, "action": "test1"}
        message2 = {"id": 2, "action": "test2"}
        self.broker.publish(queue, message1)
        self.broker.publish(queue, message2)

        # Mock para o callback
        callback = Mock()

        # Act
        self.broker.consume(queue, callback)

        # Assert
        assert callback.call_count == 2
        callback.assert_any_call(message1)
        callback.assert_any_call(message2)

    def test_consume_empty_queue(self):
        """Teste de consumo de fila vazia."""
        # Arrange
        queue = "empty_queue"
        callback = Mock()

        # Act
        self.broker.consume(queue, callback)

        # Assert
        callback.assert_not_called()

    def test_consume_after_close(self):
        """Teste de consumo após fechamento da conexão."""
        # Arrange
        queue = "test_queue"
        message = {"id": 1, "action": "test"}
        self.broker.publish(queue, message)
        self.broker.close()
        callback = Mock()

        # Act & Assert
        with pytest.raises(ConnectionError):
            self.broker.consume(queue, callback)

    def test_close(self):
        """Teste de fechamento da conexão."""
        # Act
        self.broker.close()

        # Assert
        assert not self.broker.is_connected

    @pytest.mark.asyncio
    async def test_publish_async(self):
        """Teste de publicação assíncrona."""
        # Arrange
        queue = "async_queue"
        message = {"id": 1, "action": "async_test"}

        # Act
        await self.broker.publish_async(queue, message)

        # Assert
        assert queue in self.broker.messages
        assert message in self.broker.messages[queue]

    @pytest.mark.asyncio
    async def test_publish_async_after_close(self):
        """Teste de publicação assíncrona após fechamento."""
        # Arrange
        queue = "async_queue"
        message = {"id": 1, "action": "async_test"}
        self.broker.close()

        # Act & Assert
        with pytest.raises(ConnectionError):
            await self.broker.publish_async(queue, message)

    def test_default_publish_async_implementation(self):
        """Teste da implementação padrão de publish_async."""

        # Arrange
        class SimpleMessageBroker(MessageBroker):
            def publish(self, queue: str, message: Dict[str, Any]) -> None:
                pass

            def consume(self, queue: str, callback: Callable[[Dict[str, Any]], None]) -> None:
                pass

            def close(self) -> None:
                pass

        broker = SimpleMessageBroker()
        queue = "test_queue"
        message = {"id": 1, "action": "test"}

        # Act & Assert
        with patch.object(broker, 'publish') as mock_publish:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(broker.publish_async(queue, message))

            mock_publish.assert_called_once_with(queue, message)