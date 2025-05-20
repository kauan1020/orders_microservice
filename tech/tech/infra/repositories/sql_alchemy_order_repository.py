from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from tech.domain.entities.orders import Order
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.infra.repositories.sql_alchemy_models import SQLAlchemyOrder


class SQLAlchemyOrderRepository(OrderRepository):
    """
    SQLAlchemy implementation of the OrderRepository interface.

    This repository handles all CRUD operations for the Order entity,
    interacting with the database via SQLAlchemy and mapping SQLAlchemy
    objects to domain models.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session (Session): A SQLAlchemy session used for database operations.
                               The session should be managed by the caller (opened,
                               committed, and closed appropriately).
        """
        self.session = session

    def _to_domain_order(self, db_order: SQLAlchemyOrder) -> Order:
        """
        Convert a SQLAlchemyOrder instance to a domain Order instance.

        This method acts as a mapper between the SQLAlchemy model and the domain model,
        ensuring the repository returns instances of the domain model.

        Args:
            db_order (SQLAlchemyOrder): The SQLAlchemy model instance to convert.

        Returns:
            Order: The domain model instance corresponding to the given SQLAlchemy model.
        """
        order = Order(
            id=db_order.id,
            total_price=db_order.total_price,
            product_ids=db_order.product_ids,
            status=db_order.status
        )


        if hasattr(db_order, 'user_name'):
            order.user_name = db_order.user_name
        if hasattr(db_order, 'user_email'):
            order.user_email = db_order.user_email

        return order

    def add(self, order: Order) -> Order:
        """
        Add a new order to the database.

        Converts the domain Order object into a SQLAlchemyOrder object and persists it
        in the database. Updates the `id` of the Order object with the generated ID.

        Args:
            order (Order): The domain Order object to be added.

        Returns:
            Order: The added Order object with an updated `id` field.
        """
        order_dict = {
            'total_price': order.total_price,
            'product_ids': order.product_ids,
            'status': order.status
        }

        if hasattr(order, 'user_name'):
            order_dict['user_name'] = order.user_name
        if hasattr(order, 'user_email'):
            order_dict['user_email'] = order.user_email

        db_order = SQLAlchemyOrder(**order_dict)
        self.session.add(db_order)
        self.session.commit()
        self.session.refresh(db_order)

        return self._to_domain_order(db_order)

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """
        Fetch an order by its unique ID.

        Args:
            order_id (int): The unique identifier of the order.

        Returns:
            Optional[Order]: The Order object if found, or None if no order with the given ID exists.
        """
        db_order = self.session.scalar(select(SQLAlchemyOrder).where(SQLAlchemyOrder.id == order_id))
        return self._to_domain_order(db_order) if db_order else None

    def list_orders(self, limit: int, skip: int) -> List[Order]:
        """
        Retrieve a list of orders with pagination.

        This method returns a subset of orders based on the limit and skip values,
        which can be used for pagination.

        Args:
            limit (int): The maximum number of orders to retrieve.
            skip (int): The number of orders to skip before starting to collect the results.

        Returns:
            List[Order]: A list of Order objects within the specified range.
        """
        db_orders = self.session.scalars(select(SQLAlchemyOrder).limit(limit).offset(skip)).all()
        return [self._to_domain_order(db_order) for db_order in db_orders]

    def update(self, order: Order) -> Order:
        """
        Update an existing order's information in the database.

        Finds the order in the database by its ID and updates its fields with the
        values provided in the domain Order object. Only fields present in the domain
        Order are updated.

        Args:
            order (Order): The domain Order object with updated information.

        Returns:
            Order: The updated Order object.
        """
        db_order = self.session.scalar(select(SQLAlchemyOrder).where(SQLAlchemyOrder.id == order.id))
        if db_order:
            db_order.total_price = order.total_price
            db_order.product_ids = order.product_ids
            db_order.status = order.status

            if hasattr(order, 'user_name') and hasattr(db_order, 'user_name'):
                db_order.user_name = order.user_name
            if hasattr(order, 'user_email') and hasattr(db_order, 'user_email'):
                db_order.user_email = order.user_email

            self.session.commit()
            self.session.refresh(db_order)

        return self._to_domain_order(db_order)

    def delete(self, order: Order) -> None:
        """
        Delete an order from the database.

        Finds the order in the database by its ID and removes it from the database.
        If the order does not exist, no action is taken.

        Args:
            order (Order): The domain Order object representing the order to delete.
        """
        db_order = self.session.scalar(select(SQLAlchemyOrder).where(SQLAlchemyOrder.id == order.id))
        if db_order:
            self.session.delete(db_order)
            self.session.commit()