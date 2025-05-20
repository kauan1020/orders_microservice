import os
from typing import Optional
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.infra.gateways.http_product_gateway import HttpProductGateway
from tech.infra.gateways.circuit_breaker_product_gateway import CircuitBreakerProductGateway


class ProductGatewayFactory:
    @staticmethod
    def create(
            resilience_mode: Optional[str] = None,
            failure_threshold: int = 5,
            recovery_timeout: float = 30.0,
            half_open_calls: int = 1
    ) -> ProductGateway:
        if resilience_mode is None:
            resilience_mode = os.getenv("PRODUCT_GATEWAY_RESILIENCE", "circuit_breaker")

        resilience_mode = resilience_mode.lower()

        if resilience_mode == "none":
            return HttpProductGateway()
        elif resilience_mode == "circuit_breaker":
            return CircuitBreakerProductGateway(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )
        else:
            return CircuitBreakerProductGateway(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )