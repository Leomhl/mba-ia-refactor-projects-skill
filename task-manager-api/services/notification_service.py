"""Email notifications.

The SMTP credentials were fixed in the constructor, password included. They
now come from configuration, and the transport is injectable — sending email
no longer requires a real SMTP server to be tested (playbook RP-05).

The class remains unused in the API flow, as in the original code. Wiring it
into task assignment is a product decision, recorded under "Out of scope" in
the audit report.
"""
import logging
import smtplib
from email.message import EmailMessage

from config.settings import settings
from models.user import agora

logger = logging.getLogger(__name__)


class SmtpTransport:
    """Real transport. For tests, inject any other object exposing `send`."""

    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def send(self, mensagem):
        with smtplib.SMTP(self.host, self.port) as servidor:
            servidor.starttls()
            if self.user:
                servidor.login(self.user, self.password)
            servidor.send_message(mensagem)


class NotificationService:
    def __init__(self, transport=None, remetente=None):
        self.transport = transport or SmtpTransport(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
        )
        self.remetente = remetente or settings.SMTP_USER
        self.notifications = []

    def send_email(self, to, subject, body):
        if not self.remetente:
            logger.warning('notificacao.smtp_nao_configurado')
            return False

        mensagem = EmailMessage()
        mensagem['From'] = self.remetente
        mensagem['To'] = to
        mensagem['Subject'] = subject
        mensagem.set_content(body)

        try:
            self.transport.send(mensagem)
            logger.info('notificacao.enviada', extra={'assunto': subject})
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception('notificacao.falha_envio')
            return False

    def notify_task_assigned(self, user, task):
        assunto = f'Nova task atribuída: {task.title}'
        corpo = (
            f'Olá {user.name},\n\n'
            f"A task '{task.title}' foi atribuída a você.\n\n"
            f'Prioridade: {task.priority}\nStatus: {task.status}'
        )
        enviado = self.send_email(user.email, assunto, corpo)

        self.notifications.append({
            'type': 'task_assigned',
            'user_id': user.id,
            'task_id': task.id,
            'timestamp': agora(),
        })
        return enviado

    def notify_task_overdue(self, user, task):
        assunto = f'Task atrasada: {task.title}'
        corpo = (
            f'Olá {user.name},\n\n'
            f"A task '{task.title}' está atrasada!\n\n"
            f'Data limite: {task.due_date}'
        )
        return self.send_email(user.email, assunto, corpo)

    def get_notifications(self, user_id):
        return [n for n in self.notifications if n['user_id'] == user_id]
