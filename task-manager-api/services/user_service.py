"""User and authentication business rules."""
from middlewares.error_handler import (ConflictError, ForbiddenError,
                                       NotFoundError, UnauthorizedError,
                                       ValidationError)
from models.user import User
from validators import validar_email, validar_role, validar_senha


class UserService:
    def __init__(self, user_repository, task_repository):
        self.users = user_repository
        self.tasks = task_repository

    def listar(self, limite, offset):
        return [
            {**usuario.to_dict(), 'task_count': total}
            for usuario, total in self.users.listar_com_contagem(limite, offset)
        ]

    def obter(self, user_id, limite, offset):
        usuario = self.users.obter(user_id)
        if usuario is None:
            raise NotFoundError('Usuário não encontrado')

        dados = usuario.to_dict()
        dados['tasks'] = [
            t.to_dict() for t in self.tasks.listar_por_usuario(user_id, limite, offset)
        ]
        return dados

    def listar_tarefas(self, user_id, limite, offset):
        if self.users.obter(user_id) is None:
            raise NotFoundError('Usuário não encontrado')
        return [t.to_dict() for t in self.tasks.listar_por_usuario(user_id, limite, offset)]

    def criar(self, dados):
        if not dados:
            raise ValidationError('Dados inválidos')

        nome = (dados.get('name') or '').strip()
        if not nome:
            raise ValidationError('Nome é obrigatório')

        email = validar_email((dados.get('email') or '').strip())
        senha = validar_senha(dados.get('password'))
        role = validar_role(dados.get('role', 'user'))

        if self.users.obter_por_email(email) is not None:
            raise ConflictError('Email já cadastrado')

        usuario = User()
        usuario.name = nome
        usuario.email = email
        usuario.set_password(senha)
        usuario.role = role

        return self.users.salvar(usuario).to_dict()

    def atualizar(self, user_id, dados):
        usuario = self.users.obter(user_id)
        if usuario is None:
            raise NotFoundError('Usuário não encontrado')
        if not dados:
            raise ValidationError('Dados inválidos')

        if 'name' in dados:
            usuario.name = dados['name']

        if 'email' in dados:
            email = validar_email(dados['email'])
            existente = self.users.obter_por_email(email)
            if existente is not None and existente.id != user_id:
                raise ConflictError('Email já cadastrado')
            usuario.email = email

        if 'password' in dados:
            usuario.set_password(validar_senha(dados['password']))

        if 'role' in dados:
            usuario.role = validar_role(dados['role'])

        if 'active' in dados:
            usuario.active = bool(dados['active'])

        return self.users.salvar(usuario).to_dict()

    def remover(self, user_id):
        usuario = self.users.obter(user_id)
        if usuario is None:
            raise NotFoundError('Usuário não encontrado')

        # Tasks are removed by the cascade declared in the schema, instead of
        # a loop in the handler (playbook RP-09).
        self.users.remover(usuario)

    def autenticar(self, dados):
        if not dados:
            raise ValidationError('Dados inválidos')

        email = dados.get('email')
        senha = dados.get('password')
        if not email or not senha:
            raise ValidationError('Email e senha são obrigatórios')

        usuario = self.users.obter_por_email(email)
        if usuario is None or not usuario.check_password(senha):
            raise UnauthorizedError('Credenciais inválidas')

        if not usuario.active:
            raise ForbiddenError('Usuário inativo')

        return {
            'message': 'Login realizado com sucesso',
            'user': usuario.to_dict(),
            # Placeholder kept for compatibility: no route verifies it.
            # Replacing it with a signed JWT changes the contract for every
            # client and is recorded under "Out of scope" in the audit
            # report.
            'token': f'fake-jwt-token-{usuario.id}',
        }
