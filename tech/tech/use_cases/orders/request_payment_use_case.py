from tech.domain.entities.orders import Order, OrderStatus
from tech.interfaces.repositories.order_repository import OrderRepository
from tech.interfaces.message_broker import MessageBroker


class RequestPaymentUseCase:
    """
    Caso de uso para solicitar o processamento de pagamento para um pedido.
    """

    def __init__(self, order_repository: OrderRepository, message_broker: MessageBroker):
        """
        Inicializa o caso de uso com as dependências necessárias.
        """
        self.order_repository = order_repository
        self.message_broker = message_broker

    def execute(self, order_id: int) -> Order:
        """
        Solicita o processamento de pagamento para um pedido específico.

        Args:
            order_id: ID do pedido para o qual o pagamento será solicitado.

        Returns:
            O pedido atualizado com o novo status.

        Raises:
            ValueError: Se o pedido não for encontrado.
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        payment_request = {
            "order_id": order.id,
            "amount": order.total_price,
            "customer_info": {
                "name": order.user_name if hasattr(order, 'user_name') else None,
                "email": order.user_email if hasattr(order, 'user_email') else None,
                "cpf": order.user_cpf if hasattr(order, 'user_cpf') else None
            }
        }

        try:
            self.message_broker.publish(queue="payment_requests", message=payment_request)
            print(f"Mensagem de pagamento publicada com sucesso para o pedido {order_id}")

            order.status = OrderStatus.AWAITING_PAYMENT
            updated_order = self.order_repository.update(order)

            return updated_order
        except Exception as e:
            error_msg = f"Erro ao publicar mensagem de pagamento: {str(e)}"
            print(error_msg)
            raise ValueError(error_msg)