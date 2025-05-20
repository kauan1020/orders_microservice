import os
import traceback
from typing import Dict, Any, List
from tech.interfaces.gateways.product_gateway import ProductGateway
from tech.infra.gateways.http_product_gateway import HttpProductGateway
from tech.infra.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class CircuitBreakerProductGateway(ProductGateway):
    """
    Implements a Circuit Breaker pattern for the ProductGateway.

    This implementation monitors failures when communicating with the product service
    and prevents repeated failures by "opening" the circuit after a threshold
    is reached. It will periodically attempt to "close" the circuit by allowing
    test requests to pass through.
    """

    # Usar uma única instância compartilhada do circuit breaker
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
        self.http_gateway = HttpProductGateway()

        # Usar um circuit breaker compartilhado entre instâncias
        if CircuitBreakerProductGateway._circuit_breaker is None:
            CircuitBreakerProductGateway._circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_calls=half_open_calls
            )

        self.circuit_breaker = CircuitBreakerProductGateway._circuit_breaker
        print(
            f"CircuitBreakerProductGateway initialized with threshold={failure_threshold}, timeout={recovery_timeout}")
        print(f"Circuit breaker object ID: {id(self.circuit_breaker)}")

    async def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Retrieve a product by its ID with circuit breaker protection.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            A dictionary containing the product details.

        Raises:
            ValueError: If the circuit is open or if the product is not found.
        """
        try:
            print(f"CircuitBreakerProductGateway.get_product: Getting product {product_id}")
            print(
                f"Current circuit state: {self.circuit_breaker.state.value}, failures: {self.circuit_breaker.failure_count}")

            return await self.circuit_breaker.execute(
                self.http_gateway.get_product,
                product_id
            )
        except CircuitOpenError as e:
            print(f"CircuitOpenError caught: {str(e)}")
            raise ValueError(f"Product service is currently unavailable. Please try again later.")
        except Exception as e:
            print(f"Unexpected error in get_product: {str(e)}")
            traceback.print_exc()
            raise

    async def get_products(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple products by their IDs with circuit breaker protection.

        Args:
            product_ids: A list of product IDs to retrieve.

        Returns:
            A list of dictionaries containing product details.

        Raises:
            ValueError: If the circuit is open or if any product is not found.
        """
        try:
            print(f"CircuitBreakerProductGateway.get_products: Getting products {product_ids}")
            print(
                f"Current circuit state: {self.circuit_breaker.state.value}, failures: {self.circuit_breaker.failure_count}")

            result = await self.circuit_breaker.execute(
                self.http_gateway.get_products,
                product_ids
            )
            print(f"Successfully retrieved {len(result)} products")
            return result

        except CircuitOpenError as e:
            print(f"CircuitOpenError caught: {str(e)}")
            raise ValueError(f"Product service is currently unavailable. Please try again later.")
        except Exception as e:
            print(f"Unexpected error in get_products: {str(e)}")
            print(f"Exception type: {type(e)}")
            traceback.print_exc()
            raise