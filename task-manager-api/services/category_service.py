"""Category business rules."""
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category


class CategoryService:
    def __init__(self, category_repository):
        self.categories = category_repository

    def listar(self):
        return [
            {**categoria.to_dict(), 'task_count': total}
            for categoria, total in self.categories.listar_com_contagem()
        ]

    def criar(self, dados):
        if not dados:
            raise ValidationError('Dados inválidos')

        nome = (dados.get('name') or '').strip()
        if not nome:
            raise ValidationError('Nome é obrigatório')

        categoria = Category()
        categoria.name = nome
        categoria.description = dados.get('description', '')
        categoria.color = dados.get('color', '#000000')

        return self.categories.salvar(categoria).to_dict()

    def atualizar(self, category_id, dados):
        categoria = self.categories.obter(category_id)
        if categoria is None:
            raise NotFoundError('Categoria não encontrada')
        if not dados:
            raise ValidationError('Dados inválidos')

        if 'name' in dados:
            categoria.name = dados['name']
        if 'description' in dados:
            categoria.description = dados['description']
        if 'color' in dados:
            categoria.color = dados['color']

        return self.categories.salvar(categoria).to_dict()

    def remover(self, category_id):
        categoria = self.categories.obter(category_id)
        if categoria is None:
            raise NotFoundError('Categoria não encontrada')

        # The category's tasks become unclassified (SET NULL declared in the
        # schema), instead of pointing at a nonexistent id.
        self.categories.remover(categoria)
