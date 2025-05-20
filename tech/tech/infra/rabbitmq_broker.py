import json
import pika
from typing import Callable, Dict, Any
from tech.interfaces.message_broker import MessageBroker


class RabbitMQBroker(MessageBroker):
    """
    Implementação de MessageBroker usando RabbitMQ para comunicação assíncrona.

    Esta classe gerencia conexões com o servidor RabbitMQ, garantindo a entrega
    confiável de mensagens entre os microsserviços.
    """

    def __init__(self, host: str, port: int, user: str, password: str):
        """
        Inicializa a conexão com RabbitMQ.
        """
        credentials = pika.PlainCredentials(user, password)
        self.connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=5,  # Tenta se conectar 5 vezes
            retry_delay=5  # Espera 5 segundos entre tentativas
        )

        try:
            print(f"Tentando conectar ao RabbitMQ em {host}:{port}")
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()
            print("Conexão com RabbitMQ estabelecida com sucesso")
        except Exception as e:
            print(f"Erro ao conectar ao RabbitMQ: {str(e)}")
            # Não levante a exceção imediatamente, permita lazy initialization
            self.connection = None
            self.channel = None

    def _ensure_connection(self):
        """
        Garante que a conexão está estabelecida antes de usar.
        """
        if self.connection is None or not self.connection.is_open:
            try:
                print("Tentando reestabelecer conexão com RabbitMQ")
                self.connection = pika.BlockingConnection(self.connection_params)
                self.channel = self.connection.channel()
                print("Conexão com RabbitMQ reestabelecida")
            except Exception as e:
                print(f"Falha ao reconectar com RabbitMQ: {str(e)}")
                raise

    def publish(self, queue: str, message: dict) -> None:
        """
        Publica uma mensagem em uma fila RabbitMQ.
        """
        self._ensure_connection()

        try:
            self.channel.queue_declare(queue=queue, durable=True)
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
        except Exception as e:
            print(f"Erro ao publicar mensagem: {str(e)}")
            # Tenta reconectar para próxima tentativa
            self.connection = None
            raise

    def consume(self, queue: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Consome mensagens de uma fila RabbitMQ.

        Configura um consumidor que processa mensagens continuamente até
        que a conexão seja encerrada.

        Args:
            queue: Nome da fila de onde as mensagens serão consumidas.
            callback: Função que será chamada para processar cada mensagem.
        """

        def _callback(ch, method, properties, body):
            message = json.loads(body)
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue, on_message_callback=_callback)
        self.channel.start_consuming()

    def close(self) -> None:
        """
        Fecha a conexão com RabbitMQ.

        Garante a liberação adequada dos recursos do broker.
        """
        if self.connection and self.connection.is_open:
            self.connection.close()