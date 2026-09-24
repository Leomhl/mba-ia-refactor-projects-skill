"""Category queries."""
from sqlalchemy import func, select

from database import db
from models.category import Category
from models.task import Task


class CategoryRepository:
    def obter(self, category_id):
        return db.session.get(Category, category_id)

    def listar_com_contagem(self):
        """Categories with task totals, in a single query."""
        stmt = (
            select(Category, func.count(Task.id))
            .outerjoin(Task, Task.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.id)
        )
        return db.session.execute(stmt).all()

    def total(self):
        return db.session.scalar(select(func.count(Category.id)))

    def salvar(self, category):
        db.session.add(category)
        db.session.commit()
        return category

    def remover(self, category):
        db.session.delete(category)
        db.session.commit()
