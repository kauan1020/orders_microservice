import pytest
from unittest.mock import Mock, patch, MagicMock, call
import pika
import json

from tech.infra.rabbitmq_broker import RabbitMQBroker


class TestRabbitMQBroker:
    """Unit tests for the RabbitMQBroker."""

    def setup_method(self):
        """Set up test dependencies."""
        # Mock pika connection and channel
        self.mock_connection = MagicMock()
        self.mock_channel = MagicMock()
        self.mock_connection.channel.return_value = self.mock_channel

        # Mock credentials object (not just the class)
        self.mock_credentials = MagicMock(spec=pika.PlainCredentials)

        # Create patch for pika.BlockingConnection
        self.pika_connection_patch = patch('pika.BlockingConnection', return_value=self.mock_connection)
        self.mock_pika_connection = self.pika_connection_patch.start()

        # Mock the PlainCredentials constructor directly
        self.credentials_patch = patch('pika.PlainCredentials', return_value=self.mock_credentials)
        self.mock_credentials_constructor = self.credentials_patch.start()

        # Test broker parameters
        self.host = "test-host"
        self.port = 5672
        self.user = "test-user"
        self.password = "test-password"

        # Create the broker
        self.broker = RabbitMQBroker(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.pika_connection_patch.stop()
        self.credentials_patch.stop()

    def test_initialization_success(self):
        """Test successful broker initialization."""
        # Assert
        self.mock_credentials_constructor.assert_called_once_with(self.user, self.password)
        self.mock_pika_connection.assert_called_once()
        assert self.broker.connection == self.mock_connection
        assert self.broker.channel == self.mock_channel

    def test_initialization_failure(self):
        """Test broker initialization with connection failure."""
        # Stop existing patches
        self.pika_connection_patch.stop()

        # Setup mock to raise exception
        with patch('pika.BlockingConnection', side_effect=Exception("Connection error")):
            # Act
            broker = RabbitMQBroker(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )

            # Assert
            assert broker.connection is None
            assert broker.channel is None

        # Restart the original patch for other tests
        self.mock_pika_connection = self.pika_connection_patch.start()

    def test_ensure_connection_already_connected(self):
        """Test _ensure_connection when already connected."""
        # Setup
        self.mock_connection.is_open = True

        # Act
        self.broker._ensure_connection()

        # Assert - The connection should not be recreated
        assert self.mock_pika_connection.call_count == 1  # Only from initialization

    def test_ensure_connection_reconnect(self):
        """Test _ensure_connection when connection is closed."""
        # Setup
        self.mock_connection.is_open = False

        # Act
        self.broker._ensure_connection()

        # Assert - The connection should be recreated
        assert self.mock_pika_connection.call_count == 2  # Initial + reconnect


    def test_ensure_connection_when_none(self):
        """Test _ensure_connection when connection is None."""
        # Setup
        self.broker.connection = None

        # Act
        self.broker._ensure_connection()

        # Assert - The connection should be recreated
        assert self.mock_pika_connection.call_count == 2  # Initial + reconnect

    def test_publish_success(self):
        """Test successful message publishing."""
        # Setup
        queue = "test_queue"
        message = {"key": "value"}

        # Act
        self.broker.publish(queue, message)

        # Assert
        self.mock_channel.queue_declare.assert_called_once_with(queue=queue, durable=True)
        self.mock_channel.basic_publish.assert_called_once()
        # Check the call arguments
        call_args = self.mock_channel.basic_publish.call_args
        assert call_args[1]["exchange"] == ''
        assert call_args[1]["routing_key"] == queue
        assert call_args[1]["body"] == json.dumps(message)
        # Properties should include delivery_mode=2 and content_type
        props = call_args[1]["properties"]
        assert props.delivery_mode == 2
        assert props.content_type == 'application/json'

    def test_publish_with_reconnection(self):
        """Test publishing with reconnection."""
        # Setup
        queue = "test_queue"
        message = {"key": "value"}
        self.broker.connection.is_open = False

        # Act
        self.broker.publish(queue, message)

        # Assert
        assert self.mock_pika_connection.call_count == 2  # Initial + reconnect
        self.mock_channel.queue_declare.assert_called_once_with(queue=queue, durable=True)
        self.mock_channel.basic_publish.assert_called_once()

    def test_publish_failure(self):
        """Test publishing with failure."""
        # Setup
        queue = "test_queue"
        message = {"key": "value"}
        self.mock_channel.basic_publish.side_effect = Exception("Publish failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            self.broker.publish(queue, message)

        assert "Publish failed" in str(exc_info.value)
        # Should set connection to None for next attempt
        assert self.broker.connection is None

    def test_consume(self):
        """Test message consumption setup."""
        # Setup
        queue = "test_queue"
        callback = Mock()

        # Act
        with patch.object(self.mock_channel, 'start_consuming') as mock_start_consuming:
            mock_start_consuming.side_effect = KeyboardInterrupt  # To exit the consume loop
            with pytest.raises(KeyboardInterrupt):
                self.broker.consume(queue, callback)

        # Assert
        self.mock_channel.queue_declare.assert_called_once_with(queue=queue, durable=True)
        self.mock_channel.basic_qos.assert_called_once_with(prefetch_count=1)
        self.mock_channel.basic_consume.assert_called_once()
        # Check that the call to basic_consume includes the queue and a callback
        call_args = self.mock_channel.basic_consume.call_args
        assert call_args[1]["queue"] == queue
        assert "on_message_callback" in call_args[1]

    def test_consume_callback(self):
        """Test the internal callback function in consume."""
        # Setup
        queue = "test_queue"
        callback = Mock()
        message = {"key": "value"}

        # Get the internal callback
        self.broker.consume(queue, callback)
        internal_callback = self.mock_channel.basic_consume.call_args[1]["on_message_callback"]

        # Mock channel, method, properties
        ch = Mock()
        method = Mock()
        method.delivery_tag = "test_tag"
        properties = Mock()

        # Act - Call the internal callback
        internal_callback(ch, method, properties, json.dumps(message).encode())

        # Assert
        callback.assert_called_once_with(message)
        ch.basic_ack.assert_called_once_with(delivery_tag=method.delivery_tag)

    def test_close_when_open(self):
        """Test closing an open connection."""
        # Setup
        self.mock_connection.is_open = True

        # Act
        self.broker.close()

        # Assert
        self.mock_connection.close.assert_called_once()

    def test_close_when_closed(self):
        """Test closing an already closed connection."""
        # Setup
        self.mock_connection.is_open = False

        # Act
        self.broker.close()

        # Assert
        self.mock_connection.close.assert_not_called()

    def test_close_when_none(self):
        """Test closing when connection is None."""
        # Setup
        self.broker.connection = None

        # Act
        self.broker.close()

        # Assert - Should not raise an error
        # No assertion needed, just checking it doesn't throw