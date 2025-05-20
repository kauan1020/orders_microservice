from tech.interfaces.repositories.order_repository import OrderRepository


class DeleteOrderUseCase(object):
    """
    Handles the deletion of an existing order by its unique ID.

    Args:
        order_repository (OrderRepository): Repository to interact with order data.
    """

    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    async def execute(self, order_id: int) -> dict:
        """
        Delete an order by its ID.

        Args:
            order_id (int): The unique identifier of the order to delete.

        Returns:
            dict: A success message confirming deletion.

        Raises:
            ValueError: If the order with the given ID does not exist.
        """

        db_order = self.order_repository.get_by_id(order_id)

        if not db_order:
            raise ValueError("Order not found")
        self.order_repository.delete(db_order)

        return {"message": "Order deleted successfully"}