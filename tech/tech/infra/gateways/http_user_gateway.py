import os
import httpx
import traceback
from typing import Dict, Any, Optional
from tech.interfaces.gateways.user_gateway import UserGateway


class HttpUserGateway(UserGateway):
    """
    HTTP implementation of UserGateway that communicates with the Users microservice.

    This gateway encapsulates the details of HTTP communication, allowing use cases
    to access user data without being coupled to the HTTP implementation details.
    """

    def __init__(self):
        """
        Initialize the HttpUserGateway with configuration from environment.

        Sets up the base URL for the users service and default timeout parameters
        for HTTP requests.
        """
        self.base_url = os.getenv("SERVICE_USERS_URL", "http://localhost:8000")
        self.timeout = 5.0  # Reduced timeout for faster failure detection
        print(f"HttpUserGateway initialized with base_url={self.base_url}, timeout={self.timeout}")

    async def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by their CPF from the Users microservice.

        Args:
            cpf (str): The user's CPF (Brazilian ID number).

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the user details,
                                     or None if no user is found.

        Raises:
            ValueError: If there's an error communicating with the users service.
        """
        print(f"HttpUserGateway.get_user_by_cpf: Fetching user with CPF {cpf} from {self.base_url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/users/cpf/{cpf}",
                    timeout=self.timeout
                )

                if response.status_code == 404:
                    print(f"User with CPF {cpf} not found (404 response)")
                    return None

                response.raise_for_status()
                user_data = response.json()
                print(f"Successfully retrieved user with CPF {cpf}")
                return user_data

            except httpx.HTTPStatusError as e:
                print(f"HTTP Status Error: {e.response.status_code}: {e.response.text}")
                raise ValueError(f"Error fetching user with CPF {cpf}: {e.response.status_code}: {e.response.text}")
            except httpx.ConnectError as e:
                print(f"Connection Error: {str(e)}")
                raise ValueError(f"Cannot connect to users service at {self.base_url}. Is it running?")
            except httpx.TimeoutException as e:
                print(f"Timeout Error: {str(e)}")
                raise ValueError(f"Request to users service timed out")
            except Exception as e:
                print(f"Unexpected error in HttpUserGateway.get_user_by_cpf: {str(e)}")
                traceback.print_exc()
                raise ValueError(f"Failed to communicate with users service: {str(e)}")