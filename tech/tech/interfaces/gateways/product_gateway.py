from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ProductGateway(ABC):
    """
    Gateway interface for accessing product data from external sources.

    This interface ensures a clean separation between use cases and the
    specific implementation that retrieves product data.
    """

    @abstractmethod
    async def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Retrieve a product by its ID.

        Args:
            product_id (int): The unique identifier of the product.

        Returns:
            Dict[str, Any]: A dictionary containing the product details.

        Raises:
            ValueError: If the product is not found.
        """
        pass

    @abstractmethod
    async def get_products(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple products by their IDs.

        Args:
            product_ids (List[int]): A list of product IDs to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing product details.

        Raises:
            ValueError: If any product is not found.
        """
        pass