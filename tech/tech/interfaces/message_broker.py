from abc import ABC, abstractmethod
from typing import Dict, Any, Callable


class MessageBroker(ABC):
    """
    Interface para sistemas de mensageria.
    """

    @abstractmethod
    def publish(self, queue: str, message: Dict[str, Any]) -> None:
        """
        Publica uma mensagem em uma fila.

        Args:
            queue: Nome da fila para publicar a mensagem
            message: Mensagem a ser publicada
        """
        pass

    @abstractmethod
    def consume(self, queue: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Consome mensagens de uma fila e processa com o callback fornecido.

        Args:
            queue: Nome da fila para consumir mensagens
            callback: Função a ser chamada quando uma mensagem for recebida
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Fecha a conexão com o sistema de mensageria.
        """
        pass

    # Método assíncrono opcional - não é obrigatório para todos os implementadores
    async def publish_async(self, queue: str, message: Dict[str, Any]) -> None:
        """
        Versão assíncrona de publish para uso com código assíncrono.

        Este método é opcional e pode ser implementado por classes concretas
        que desejam fornecer suporte assíncrono.

        Args:
            queue: Nome da fila para publicar a mensagem
            message: Mensagem a ser publicada
        """
        # Implementação padrão que chama o método síncrono
        # Implementações concretas devem sobrescrever este método
        self.publish(queue, message)