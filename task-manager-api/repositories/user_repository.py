"""User queries."""
from sqlalchemy import case, func, select

from database import db
from models.task import Task
from models.user import User


class UserRepository:
    def obter(self, user_id):
        return db.session.get(User, user_id)

    def obter_por_email(self, email):
        return db.session.scalars(select(User).where(User.email == email)).first()

    def listar_com_contagem(self, limite, offset):
        """Users with their task totals, in a single query.

        The original handler accessed `len(u.tasks)` per user, which triggers
        individual lazy loading (playbook RP-07).
        """
        stmt = (
            select(User, func.count(Task.id))
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
            .limit(limite)
            .offset(offset)
        )
        return db.session.execute(stmt).all()

    def produtividade(self):
        """Totals and completions per user, in one GROUP BY query."""
        concluidas = func.sum(case((Task.status == 'done', 1), else_=0))
        stmt = (
            select(User.id, User.name, func.count(Task.id), concluidas)
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
        )
        return db.session.execute(stmt).all()

    def total(self):
        return db.session.scalar(select(func.count(User.id)))

    def salvar(self, user):
        db.session.add(user)
        db.session.commit()
        return user

    def remover(self, user):
        db.session.delete(user)
        db.session.commit()
