"""Task business rules."""
from middlewares.error_handler import NotFoundError, ValidationError
from models.task import Task
from models.user import agora
from validators import (normalizar_tags, validar_data, validar_prioridade,
                        validar_status, validar_titulo)


class TaskService:
    def __init__(self, task_repository, user_repository, category_repository):
        self.tasks = task_repository
        self.users = user_repository
        self.categories = category_repository

    def listar(self, limite, offset):
        return [t.to_dict(incluir_relacionados=True)
                for t in self.tasks.listar(limite, offset)]

    def obter(self, task_id):
        task = self.tasks.obter(task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        return task.to_dict()

    def buscar(self, filtros, limite, offset):
        return [t.to_dict() for t in self.tasks.buscar(**filtros,
                                                       limite=limite,
                                                       offset=offset)]

    def criar(self, dados):
        if not dados:
            raise ValidationError('Dados inválidos')

        task = Task()
        task.title = validar_titulo(dados.get('title'))
        task.description = dados.get('description', '')
        task.status = validar_status(dados.get('status', 'pending'))
        task.priority = validar_prioridade(dados.get('priority', 3))
        task.user_id = self._validar_usuario(dados.get('user_id'))
        task.category_id = self._validar_categoria(dados.get('category_id'))
        task.due_date = validar_data(dados.get('due_date'))
        task.tags = normalizar_tags(dados.get('tags'))

        return self.tasks.salvar(task).to_dict()

    def atualizar(self, task_id, dados):
        task = self.tasks.obter(task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        if not dados:
            raise ValidationError('Dados inválidos')

        if 'title' in dados:
            task.title = validar_titulo(dados['title'])
        if 'description' in dados:
            task.description = dados['description']
        if 'status' in dados:
            task.status = validar_status(dados['status'])
        if 'priority' in dados:
            task.priority = validar_prioridade(dados['priority'])
        if 'user_id' in dados:
            task.user_id = self._validar_usuario(dados['user_id'])
        if 'category_id' in dados:
            task.category_id = self._validar_categoria(dados['category_id'])
        if 'due_date' in dados:
            task.due_date = validar_data(dados['due_date'], 'Formato de data inválido')
        if 'tags' in dados:
            task.tags = normalizar_tags(dados['tags'])

        task.updated_at = agora()
        return self.tasks.salvar(task).to_dict()

    def remover(self, task_id):
        task = self.tasks.obter(task_id)
        if task is None:
            raise NotFoundError('Task não encontrada')
        self.tasks.remover(task)

    def estatisticas(self):
        por_status = self.tasks.contar_por_status()
        total = sum(por_status.values())
        concluidas = por_status.get('done', 0)

        atrasadas = sum(1 for t in self.tasks.todas() if t.is_overdue())

        return {
            'total': total,
            'pending': por_status.get('pending', 0),
            'in_progress': por_status.get('in_progress', 0),
            'done': concluidas,
            'cancelled': por_status.get('cancelled', 0),
            'overdue': atrasadas,
            'completion_rate': round((concluidas / total) * 100, 2) if total else 0,
        }

    def _validar_usuario(self, user_id):
        if not user_id:
            return None
        if self.users.obter(user_id) is None:
            raise NotFoundError('Usuário não encontrado')
        return user_id

    def _validar_categoria(self, category_id):
        if not category_id:
            return None
        if self.categories.obter(category_id) is None:
            raise NotFoundError('Categoria não encontrada')
        return category_id
