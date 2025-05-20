# tech/interfaces/gateways/user_gateway.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class UserGateway(ABC):
    """
    Gateway interface for accessing user data from external sources.

    This interface ensures a clean separation between use cases and the
    specific implementation that retrieves user data.
    """

    @abstractmethod
    async def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by their CPF.

        Args:
            cpf (str): The user's CPF (Brazilian ID number).

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the user details,
                                     or None if no user is found.
        Raises:
            ValueError: If there's an error communicating with the users service.
        """
        pass