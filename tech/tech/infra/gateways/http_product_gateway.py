import os
import httpx
import traceback
from typing import Dict, Any, List
from tech.interfaces.gateways.product_gateway import ProductGateway


class HttpProductGateway(ProductGateway):
    """
    HTTP implementation of ProductGateway that communicates with the Products microservice.

    This gateway encapsulates the details of HTTP communication, allowing use cases
    to access product data without being coupled to the HTTP implementation details.
    It fetches product data by first retrieving all products and then filtering by ID,
    adapting to the structure of the Products API.
    """

    def __init__(self):
        """
        Initialize the HttpProductGateway with configuration from environment.

        Sets up the base URL for the products service and default timeout parameters
        for HTTP requests.
        """
        self.base_url = os.getenv("SERVICE_PRODUCTS_URL", "http://localhost:8002")
        self.timeout = 5.0  # Reduced timeout for faster failure detection
        print(f"HttpProductGateway initialized with base_url={self.base_url}, timeout={self.timeout}")

    async def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Retrieve a product by its ID from the Products microservice.

        This method fetches the complete list of products and filters to find
        the specific product with the requested ID.

        Args:
            product_id (int): The unique identifier of the product to retrieve.

        Returns:
            Dict[str, Any]: A dictionary containing the product details including
                            id, name, price, and category.

        Raises:
            ValueError: If the product is not found or if there's a communication
                        error with the products service.
        """
        print(f"HttpProductGateway.get_product: Fetching product {product_id} from {self.base_url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/products/",
                    timeout=self.timeout
                )
                response.raise_for_status()

                all_products = response.json()
                for product in all_products:
                    if product["id"] == product_id:
                        return product

                raise ValueError(f"Product with ID {product_id} not found")

            except httpx.HTTPStatusError as e:
                print(f"HTTP Status Error: {e.response.status_code}: {e.response.text}")
                raise ValueError(f"Error fetching products: {e.response.status_code}: {e.response.text}")
            except httpx.ConnectError as e:
                print(f"Connection Error: {str(e)}")
                raise ValueError(f"Cannot connect to products service at {self.base_url}. Is it running?")
            except httpx.TimeoutException as e:
                print(f"Timeout Error: {str(e)}")
                raise ValueError(f"Request to products service timed out")
            except Exception as e:
                print(f"Unexpected error in HttpProductGateway.get_product: {str(e)}")
                traceback.print_exc()
                raise ValueError(f"Failed to communicate with products service: {str(e)}")

    async def get_products(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple products by their IDs from the Products microservice.

        This method optimizes network usage by fetching all products in a single
        request and then filtering the results to include only the products with
        the requested IDs.

        Args:
            product_ids (List[int]): A list of product IDs to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing product details
                                 for each requested product ID.

        Raises:
            ValueError: If any product is not found or if there's a communication
                        error with the products service. The error message will
                        specify which product ID was not found.
        """
        print(f"HttpProductGateway.get_products: Fetching products {product_ids} from {self.base_url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                print(f"Sending request to {self.base_url}/products/")
                response = await client.get(f"{self.base_url}/products/")
                print(f"Response status: {response.status_code}")
                response.raise_for_status()

                all_products = response.json()
                products = []

                for product_id in product_ids:
                    found = False
                    for product in all_products:
                        if product["id"] == product_id:
                            products.append(product)
                            found = True
                            break

                    if not found:
                        raise ValueError(f"Product with ID {product_id} not found")

                print(f"Successfully retrieved {len(products)} products")
                return products

        except httpx.HTTPStatusError as e:
            print(f"HTTP Status Error: {e.response.status_code}: {e.response.text}")
            raise ValueError(f"Error fetching products: {e.response.status_code}: {e.response.text}")
        except httpx.ConnectError as e:
            print(f"Connection Error: {str(e)}")
            raise ValueError(f"Cannot connect to products service at {self.base_url}. Is it running?")
        except httpx.TimeoutException as e:
            print(f"Timeout Error: {str(e)}")
            raise ValueError(f"Request to products service timed out")
        except Exception as e:
            print(f"Unexpected error in HttpProductGateway.get_products: {str(e)}")
            print(f"Exception type: {type(e)}")
            traceback.print_exc()
            raise ValueError(f"Failed to communicate with products service: {str(e)}")