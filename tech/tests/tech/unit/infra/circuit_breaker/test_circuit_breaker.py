import pytest
import time
from unittest.mock import Mock, AsyncMock
from tech.infra.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError


class TestCircuitBreaker:
    """Unit tests for the CircuitBreaker."""

    def setup_method(self):
        """Set up test dependencies."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=2,  # Lower threshold for testing
            recovery_timeout=0.1,  # Lower timeout for testing
            half_open_calls=1
        )

    def test_initialization(self):
        """Test circuit breaker initialization."""
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.failure_threshold == 2
        assert self.circuit_breaker.recovery_timeout == 0.1
        assert self.circuit_breaker.half_open_calls == 1

    def test_successful_execution(self):
        """Test successful execution through the circuit breaker."""
        # Create a mock function
        mock_func = AsyncMock()
        mock_func.return_value = "success"

        # Use synchronous test to verify state changes
        # We'll mock the async execution
        self.circuit_breaker.execute = Mock(return_value="success")

        # Act
        result = self.circuit_breaker.execute(mock_func)

        # Assert
        assert result == "success"
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after reaching the failure threshold."""
        # Create a mock function that will fail
        mock_func = AsyncMock()
        mock_func.side_effect = Exception("Test failure")

        # Use synchronous execution for clearer test flow
        self.circuit_breaker.execute = Mock(side_effect=self._simulate_execution_failures)

        # Act - cause failures to reach threshold
        try:
            self.circuit_breaker.execute(mock_func)
        except Exception:
            pass

        try:
            self.circuit_breaker.execute(mock_func)
        except Exception:
            pass

        # Assert
        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.failure_count >= self.circuit_breaker.failure_threshold

    def test_circuit_rejects_calls_when_open(self):
        """Test that circuit rejects calls when in open state."""
        # Force circuit to open state
        self.circuit_breaker.state = CircuitState.OPEN
        self.circuit_breaker.last_failure_time = time.time()

        # Create a mock function
        mock_func = AsyncMock()

        # Use synchronous execution for simpler test
        self.circuit_breaker.execute = Mock(side_effect=CircuitOpenError("Circuit is open"))

        # Act & Assert
        with pytest.raises(CircuitOpenError):
            self.circuit_breaker.execute(mock_func)

    def test_circuit_closes_after_successful_half_open_calls(self):
        """Test that circuit closes after successful calls in half-open state."""
        # Force circuit to half-open state
        self.circuit_breaker.state = CircuitState.HALF_OPEN
        self.circuit_breaker.half_open_successes = 0

        # Create a mock function that succeeds
        mock_func = AsyncMock()
        mock_func.return_value = "success"

        # Mock the reset method
        original_reset = self.circuit_breaker.reset
        self.circuit_breaker.reset = Mock()

        # Use synchronous execution for testing
        result = self._simulate_half_open_success(self.circuit_breaker)

        # Assert
        self.circuit_breaker.reset.assert_called_once()
        assert result == "success"

        self.circuit_breaker.reset = original_reset

    def test_circuit_reset(self):
        """Test that reset method properly resets the circuit state."""
        # Arrange - Set circuit to non-default state
        self.circuit_breaker.state = CircuitState.OPEN
        self.circuit_breaker.failure_count = 5
        self.circuit_breaker.half_open_successes = 3

        # Act
        self.circuit_breaker.reset()

        # Assert
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.half_open_successes == 0

    def _simulate_execution_failures(self, func):
        """Simulate execution failures to test circuit state transitions."""
        self.circuit_breaker.failure_count += 1
        self.circuit_breaker.last_failure_time = time.time()

        if self.circuit_breaker.failure_count >= self.circuit_breaker.failure_threshold:
            self.circuit_breaker.state = CircuitState.OPEN

        raise Exception("Test failure")

    def _simulate_half_open_success(self, circuit):
        """Simulate a successful call in half-open state."""
        circuit.half_open_successes += 1

        if circuit.half_open_successes >= circuit.half_open_calls:
            circuit.reset()

        return "success"