from enum import Enum
import time
import asyncio
from typing import Callable, Any, TypeVar, Awaitable

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'


class CircuitBreaker:
    def __init__(
            self,
            failure_threshold: int = 5,
            recovery_timeout: float = 30.0,
            half_open_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_calls = half_open_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_successes = 0
        print(f"Circuit Breaker initialized with threshold={failure_threshold}, timeout={recovery_timeout}")

    async def execute(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        print(
            f"Circuit Breaker execute called - current state: {self.state.value}, failure count: {self.failure_count}")

        if self.state == CircuitState.OPEN:
            time_since_failure = time.time() - self.last_failure_time
            print(
                f"Circuit is OPEN. Time since last failure: {time_since_failure:.2f}s, recovery timeout: {self.recovery_timeout}s")

            if time_since_failure > self.recovery_timeout:
                print(f"Recovery timeout reached, transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
            else:
                print(f"Circuit still OPEN. Raising CircuitOpenError")
                raise CircuitOpenError("Service is currently unavailable. Please try again later.")

        try:
            print(f"Executing function through circuit breaker")
            result = await func(*args, **kwargs)

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                print(f"Success in HALF_OPEN state. Successes: {self.half_open_successes}/{self.half_open_calls}")

                if self.half_open_successes >= self.half_open_calls:
                    print(f"Enough successes in HALF_OPEN state, resetting circuit to CLOSED")
                    self.reset()

            return result

        except Exception as e:
            print(f"Function execution failed: {str(e)}")
            self._handle_failure()
            raise e

    def _handle_failure(self):
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            print(f"Failure in HALF_OPEN state, returning to OPEN")
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            print(f"Failure in CLOSED state. Count: {self.failure_count}/{self.failure_threshold}")

            if self.failure_count >= self.failure_threshold:
                print(f"Threshold reached, transitioning to OPEN")
                self.state = CircuitState.OPEN

    def reset(self):
        print(f"Resetting circuit breaker to CLOSED state")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_successes = 0


class CircuitOpenError(Exception):
    pass