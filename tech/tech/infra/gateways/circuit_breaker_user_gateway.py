import os
import traceback
from typing import Dict, Any, Optional
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.infra.gateways.http_user_gateway import HttpUserGateway
from tech.infra.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class CircuitBreakerUserGateway(UserGateway):
    """
    Implements a Circuit Breaker pattern for the UserGateway.

    This implementation monitors failures when communicating with the user service
    and prevents repeated failures by "opening" the circuit after a threshold
    is reached. It will periodically attempt to "close" the circuit by allowing
    test requests to pass through.
    """

    _instance = None
    _circuit_breaker = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(
            self,
            failure_threshold: int = 3,
            recovery_timeout: float = 15.0,
            half_open_calls: int = 1
    ):
        self.http_gateway = HttpUserGateway()

        # Usar um circuit breaker compartilhado entre instâncias
        if CircuitBreakerUserGateway._circuit_breaker is None:
            CircuitBreakerUserGateway._circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )

        self.circuit_breaker = CircuitBreakerUserGateway._circuit_breaker
        print(f"CircuitBreakerUserGateway initialized with threshold={failure_threshold}, timeout={recovery_timeout}")
        print(f"Circuit breaker object ID: {id(self.circuit_breaker)}")

    async def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by CPF with circuit breaker protection.

        Args:
            cpf: The user's CPF (Brazilian ID number).

        Returns:
            A dictionary containing the user details, or None if no user is found.

        Raises:
            ValueError: If the circuit is open, indicating the user service is unavailable.
        """
        try:
            print(f"CircuitBreakerUserGateway.get_user_by_cpf: Getting user with CPF {cpf}")
            print(
                f"Current circuit state: {self.circuit_breaker.state.value}, failures: {self.circuit_breaker.failure_count}")

            result = await self.circuit_breaker.execute(
                self.http_gateway.get_user_by_cpf,
                cpf
            )

            if result is None:
                print(f"User with CPF {cpf} not found (normal behavior, not a service failure)")
            else:
                print(f"User with CPF {cpf} found successfully")

            return result

        except CircuitOpenError as e:
            print(f"CircuitOpenError caught: {str(e)}")
            print(f"User service is unavailable, continuing without user information")
            return None

        except Exception as e:
            print(f"Unexpected error in get_user_by_cpf: {str(e)}")
            traceback.print_exc()
            return None