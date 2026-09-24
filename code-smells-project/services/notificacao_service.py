"""Order notifications.

The dispatches were inline in the HTTP handler, as `print` calls (playbook
RP-04). Concentrating them here makes the rule testable and gives a single
place to swap the simulation for a real provider.
"""
import logging

logger = logging.getLogger(__name__)


class NotificacaoService:
    """Simulates the notification channels, recording structured logs.

    Observable behavior is unchanged from the original code — no message was
    ever actually sent, only printed.
    """

    CANAIS = ("email", "sms", "push")

    def pedido_criado(self, pedido_id, usuario_id):
        for canal in self.CANAIS:
            logger.info(
                "notificacao.pedido_criado",
                extra={"canal": canal, "pedido_id": pedido_id, "usuario_id": usuario_id},
            )

    def status_alterado(self, pedido_id, status):
        """Notifies only the transitions the business cares about."""
        if status not in ("aprovado", "cancelado"):
            return

        logger.info(
            "notificacao.status_alterado",
            extra={"pedido_id": pedido_id, "status": status},
        )
