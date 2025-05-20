import os
from typing import Optional
from tech.interfaces.gateways.user_gateway import UserGateway
from tech.infra.gateways.http_user_gateway import HttpUserGateway
from tech.infra.gateways.circuit_breaker_user_gateway import CircuitBreakerUserGateway


class UserGatewayFactory:
    @staticmethod
    def create(
            resilience_mode: Optional[str] = None,
            failure_threshold: int = 5,
            recovery_timeout: float = 30.0,
            half_open_calls: int = 1
    ) -> UserGateway:
        if resilience_mode is None:
            resilience_mode = os.getenv("USER_GATEWAY_RESILIENCE", "circuit_breaker")

        resilience_mode = resilience_mode.lower()

        if resilience_mode == "none":
            return HttpUserGateway()
        elif resilience_mode == "circuit_breaker":
            return CircuitBreakerUserGateway(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )
        else:
            return CircuitBreakerUserGateway(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )