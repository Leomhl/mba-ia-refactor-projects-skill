"""Report aggregations.

The summary report was assembled inside the handler, with more than twenty
queries — one per status, one per priority and one per user (playbook RP-04,
RP-07).
"""
from datetime import timedelta

from middlewares.error_handler import NotFoundError
from models.user import agora


class ReportService:
    def __init__(self, task_repository, user_repository, category_repository):
        self.tasks = task_repository
        self.users = user_repository
        self.categories = category_repository

    def resumo(self):
        por_status = self.tasks.contar_por_status()
        por_prioridade = self.tasks.contar_por_prioridade()

        atrasadas = [t for t in self.tasks.todas() if t.is_overdue()]
        momento = agora()

        sete_dias_atras = momento - timedelta(days=7)

        return {
            'generated_at': str(momento),
            'overview': {
                'total_tasks': self.tasks.total(),
                'total_users': self.users.total(),
                'total_categories': self.categories.total(),
            },
            'tasks_by_status': {
                'pending': por_status.get('pending', 0),
                'in_progress': por_status.get('in_progress', 0),
                'done': por_status.get('done', 0),
                'cancelled': por_status.get('cancelled', 0),
            },
            'tasks_by_priority': {
                'critical': por_prioridade.get(1, 0),
                'high': por_prioridade.get(2, 0),
                'medium': por_prioridade.get(3, 0),
                'low': por_prioridade.get(4, 0),
                'minimal': por_prioridade.get(5, 0),
            },
            'overdue': {
                'count': len(atrasadas),
                'tasks': [self._resumo_atraso(t, momento) for t in atrasadas],
            },
            'recent_activity': {
                'tasks_created_last_7_days': self.tasks.criadas_desde(sete_dias_atras),
                'tasks_completed_last_7_days': self.tasks.concluidas_desde(sete_dias_atras),
            },
            'user_productivity': [
                {
                    'user_id': user_id,
                    'user_name': nome,
                    'total_tasks': total,
                    'completed_tasks': concluidas or 0,
                    'completion_rate': round(((concluidas or 0) / total) * 100, 2) if total else 0,
                }
                for user_id, nome, total, concluidas in self.users.produtividade()
            ],
        }

    def por_usuario(self, user_id):
        usuario = self.users.obter(user_id)
        if usuario is None:
            raise NotFoundError('Usuário não encontrado')

        tarefas = self.tasks.listar_por_usuario(user_id, limite=None, offset=0)

        contagem = {'done': 0, 'pending': 0, 'in_progress': 0, 'cancelled': 0}
        alta_prioridade = 0
        atrasadas = 0

        for tarefa in tarefas:
            if tarefa.status in contagem:
                contagem[tarefa.status] += 1
            if tarefa.priority <= 2:
                alta_prioridade += 1
            if tarefa.is_overdue():
                atrasadas += 1

        total = len(tarefas)

        return {
            'user': {
                'id': usuario.id,
                'name': usuario.name,
                'email': usuario.email,
            },
            'statistics': {
                'total_tasks': total,
                **contagem,
                'overdue': atrasadas,
                'high_priority': alta_prioridade,
                'completion_rate': round((contagem['done'] / total) * 100, 2) if total else 0,
            },
        }

    def _resumo_atraso(self, tarefa, momento):
        from models.user import como_utc

        return {
            'id': tarefa.id,
            'title': tarefa.title,
            'due_date': str(tarefa.due_date),
            'days_overdue': (momento - como_utc(tarefa.due_date)).days,
        }
