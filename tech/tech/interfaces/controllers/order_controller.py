from fastapi import HTTPException
from tech.use_cases.orders.create_order_use_case import CreateOrderUseCase
from tech.use_cases.orders.list_orders_use_case import ListOrdersUseCase
from tech.use_cases.orders.update_order_status_use_case import UpdateOrderStatusUseCase
from tech.use_cases.orders.delete_order_use_case import DeleteOrderUseCase
from tech.interfaces.schemas.order_schema import OrderCreate
from tech.domain.entities.orders import OrderStatus

class OrderController:
    """
    Controller responsible for managing order-related operations.
    """

    def __init__(
            self,
            create_order_use_case,
            list_orders_use_case,
            update_order_status_use_case,
            delete_order_use_case,
    ):
        self.create_order_use_case = create_order_use_case
        self.list_orders_use_case = list_orders_use_case
        self.update_order_status_use_case = update_order_status_use_case
        self.delete_order_use_case = delete_order_use_case
        self.order_repository = self.list_orders_use_case.order_repository
        self.product_gateway = self.list_orders_use_case.product_gateway

    async def create_order(self, order_data: OrderCreate) -> dict:
        """
        Creates a new order and returns a formatted response.

        Args:
            order_data (OrderCreate): The data required to create a new order.

        Returns:
            dict: The formatted response containing order details.

        Raises:
            HTTPException: If any of the products are not found.
        """
        try:
            order = await self.create_order_use_case.execute(order_data)
            return order.dict()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def list_orders(self, limit: int, skip: int) -> list:
        """
        Retrieves a paginated list of orders.

        Args:
            limit (int): The maximum number of orders to return.
            skip (int): The number of orders to skip.

        Returns:
            list: A list of formatted order details.
        """

        orders = await self.list_orders_use_case.execute(limit, skip)
        return [order.dict() for order in orders]

    async def update_order_status(self, order_id: int, status: OrderStatus) -> dict:
        """
        Updates the status of an order.

        Args:
            order_id (int): The ID of the order to update.
            status (OrderStatus): The new status for the order.

        Returns:
            dict: A success message.

        Raises:
            HTTPException: If the order is not found or the update fails.
        """
        try:
            updated_order = await self.update_order_status_use_case.execute(order_id, status)
            return updated_order.dict()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def delete_order(self, order_id: int) -> dict:
        """
        Deletes an order by its unique ID.

        Args:
            order_id (int): The ID of the order to delete.

        Returns:
            dict: A success message confirming deletion.

        Raises:
            HTTPException: If the order is not found.
        """
        try:
            await self.delete_order_use_case.execute(order_id)
            return {"message": f"Order {order_id} deleted successfully"}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_order(self, order_id: int) -> dict:
        """
        Retrieves a specific order by ID with complete product details.
        """
        try:
            print(f"Buscando pedido com ID {order_id}")

            order = self.order_repository.get_by_id(order_id)
            print(f"Resultado da busca: {order}")

            if not order:
                print(f"Pedido com ID {order_id} não encontrado")
                raise ValueError(f"Order with ID {order_id} not found")

            print(f"Dados do pedido: ID={order.id}, Status={order.status}")

            product_ids = list(map(int, order.product_ids.split(','))) if order.product_ids else []
            print(f"IDs de produtos: {product_ids}")

            product_details = []

            if product_ids:
                try:
                    print(f"Buscando detalhes dos produtos...")
                    products = await self.product_gateway.get_products(product_ids)
                    product_details = [
                        {
                            "id": product["id"],
                            "name": product["name"],
                            "price": product["price"],
                        }
                        for product in products
                    ]
                    print(f"Detalhes dos produtos obtidos: {len(product_details)} produtos")
                except Exception as e:
                    print(f"Erro ao buscar detalhes dos produtos: {str(e)}")
                    product_details = [{"id": pid, "name": "Unknown", "price": 0} for pid in product_ids]

            response = {
                "id": order.id,
                "total_price": order.total_price,
                "status": order.status.value,
                "products": product_details,
            }

            if hasattr(order, 'created_at') and order.created_at:
                if hasattr(order.created_at, 'isoformat'):
                    response["created_at"] = order.created_at.isoformat()
                else:
                    response["created_at"] = str(order.created_at)

            if hasattr(order, 'updated_at') and order.updated_at:
                if hasattr(order.updated_at, 'isoformat'):
                    response["updated_at"] = order.updated_at.isoformat()
                else:
                    response["updated_at"] = str(order.updated_at)

            if hasattr(order, 'user_name') and order.user_name:
                user_info = {"name": order.user_name}

                if hasattr(order, 'user_email') and order.user_email:
                    user_info["email"] = order.user_email

                response["user_info"] = user_info

            print(f"Resposta preparada: {response}")
            return response

        except Exception as e:
            print(f"Erro no método get_order: {str(e)}")
            print(f"Tipo de erro: {type(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error retrieving order: {str(e)}")