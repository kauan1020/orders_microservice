import os
import sys
import json
import logging
import traceback
import pika
import requests
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("payment_response_consumer")

# Configurações de ambiente
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
ORDER_SERVICE_URL = os.getenv("SERVICE_ORDERS_URL", "http://localhost:8003")
PAYMENT_RESPONSES_QUEUE = "payment_responses"


class OrderUpdateService:
    """
    Serviço para atualizar o status dos pedidos após processamento de pagamento.
    """

    def __init__(self, order_service_url):
        self.order_service_url = order_service_url
        logger.info(f"OrderUpdateService initialized with URL: {order_service_url}")

    def update_order_status(self, order_id, payment_status):
        """
        Atualiza o status do pedido com base no status do pagamento.

        Args:
            order_id: ID do pedido a ser atualizado
            payment_status: Status do pagamento (APPROVED, REJECTED, etc.)

        Returns:
            Dict com o resultado da atualização
        """
        try:
            # Mapear status de pagamento para status de pedido
            order_status = self._map_payment_status_to_order_status(payment_status)
            logger.info(f"Mapeando status de pagamento {payment_status} para status de pedido {order_status}")

            if not order_status:
                logger.warning(f"Status de pagamento {payment_status} não mapeado para status de pedido")
                return {"success": False, "message": f"Status de pagamento não mapeado: {payment_status}"}

            # Chamar a API do serviço de pedidos
            update_url = f"{self.order_service_url}/{order_id}"
            logger.info(f"Atualizando pedido {order_id} para status {order_status} via URL: {update_url}")

            response = requests.put(
                update_url,
                params={"status": order_status},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 201, 202):
                logger.info(f"Pedido {order_id} atualizado com sucesso para status {order_status}")
                return {"success": True, "order": response.json()}
            else:
                logger.error(f"Erro ao atualizar pedido: {response.status_code} - {response.text}")
                return {"success": False, "status_code": response.status_code, "message": response.text}

        except requests.RequestException as e:
            logger.error(f"Erro de conexão ao atualizar pedido {order_id}: {str(e)}")
            return {"success": False, "message": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro ao atualizar pedido {order_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return {"success": False, "message": f"Erro: {str(e)}"}

    def _map_payment_status_to_order_status(self, payment_status):
        """
        Mapeia o status do pagamento para o status do pedido.

        Args:
            payment_status: Status do pagamento (APPROVED, PENDING, etc.)

        Returns:
            String com o status do pedido correspondente
        """
        # Mapeamento de status do pagamento para status do pedido
        # MODIFICADO para usar os valores corretos do enum OrderStatus
        status_map = {
            "APPROVED": "PAID",  # Modificado de PREPARING para PAID
            "PENDING": "AWAITING_PAYMENT",  # Se pagamento pendente, pedido continua aguardando
            "REJECTED": "PAYMENT_FAILED",  # Modificado de CANCELLED para PAYMENT_FAILED
            "ERROR": "PAYMENT_ERROR"  # Se erro no pagamento, pedido fica em erro
        }

        return status_map.get(payment_status)


def callback(ch, method, properties, body, order_service):
    """
    Callback para processar mensagens de resposta de pagamento.

    Args:
        ch: Channel do RabbitMQ
        method: Método da mensagem
        properties: Propriedades da mensagem
        body: Corpo da mensagem
        order_service: Serviço de atualização de pedidos
    """
    try:
        # Decodificar mensagem
        message = json.loads(body)
        logger.info(f"Mensagem de resposta de pagamento recebida: {message}")

        order_id = message.get('order_id')
        status = message.get('status')

        if not order_id or not status:
            logger.error(f"Mensagem inválida, faltando order_id ou status: {message}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Atualizar status do pedido
        result = order_service.update_order_status(order_id, status)
        logger.info(f"Resultado da atualização do pedido {order_id}: {result}")

        # Confirmar processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar mensagem: {body}")
        ch.basic_ack(delivery_tag=method.delivery_tag)  # Evitar reprocessamento de mensagens inválidas
    except Exception as e:
        logger.error(f"Erro ao processar resposta de pagamento: {str(e)}")
        logger.error(traceback.format_exc())

        # Decidir se deve reprocessar ou não
        requeue = False  # Por padrão, não recoloca na fila para evitar loops infinitos
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)


def main():
    """
    Função principal que inicia o consumidor de respostas de pagamento.
    """
    logger.info("Iniciando consumidor de respostas de pagamento")

    try:
        # Inicializar serviço de atualização de pedidos
        order_service = OrderUpdateService(ORDER_SERVICE_URL)

        # Configurar conexão com RabbitMQ
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        connection_params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )

        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        # Declarar a fila de respostas
        channel.queue_declare(queue=PAYMENT_RESPONSES_QUEUE, durable=True)

        # Configurar QoS
        channel.basic_qos(prefetch_count=1)

        # Configurar consumo com partial function para incluir order_service
        from functools import partial
        callback_with_service = partial(callback, order_service=order_service)

        channel.basic_consume(
            queue=PAYMENT_RESPONSES_QUEUE,
            on_message_callback=callback_with_service
        )

        logger.info(f"Consumindo mensagens da fila '{PAYMENT_RESPONSES_QUEUE}'")
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Consumidor interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro ao iniciar consumidor: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()