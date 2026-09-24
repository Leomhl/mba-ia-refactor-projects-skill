"""Task queries.

Uses the SQLAlchemy 2.0 API (`db.session.get` and `select`) in place of the
legacy Query API, which emits LegacyAPIWarning on the declared version
(playbook RP-14).
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from database import db
from models.task import Task


class TaskRepository:
    def obter(self, task_id):
        return db.session.get(Task, task_id)

    def listar(self, limite, offset):
        """Lists tasks with user and category already loaded.

        `joinedload` eliminates the two queries per task the handlers fired to
        fetch the user and category names (playbook RP-07).
        """
        stmt = (
            select(Task)
            .options(joinedload(Task.user), joinedload(Task.category))
            .order_by(Task.id)
            .limit(limite)
            .offset(offset)
        )
        return db.session.scalars(stmt).unique().all()

    def buscar(self, termo=None, status=None, priority=None, user_id=None,
               limite=50, offset=0):
        stmt = select(Task).options(
            joinedload(Task.user), joinedload(Task.category)
        )

        if termo:
            padrao = f'%{termo}%'
            stmt = stmt.where(or_(Task.title.like(padrao), Task.description.like(padrao)))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)

        stmt = stmt.order_by(Task.id).limit(limite).offset(offset)
        return db.session.scalars(stmt).unique().all()

    def listar_por_usuario(self, user_id, limite, offset):
        stmt = (
            select(Task)
            .options(joinedload(Task.user), joinedload(Task.category))
            .where(Task.user_id == user_id)
            .order_by(Task.id)
            .limit(limite)
            .offset(offset)
        )
        return db.session.scalars(stmt).unique().all()

    def contar_por_status(self):
        """One aggregation in place of a COUNT per status."""
        stmt = select(Task.status, func.count(Task.id)).group_by(Task.status)
        return dict(db.session.execute(stmt).all())

    def contar_por_prioridade(self):
        stmt = select(Task.priority, func.count(Task.id)).group_by(Task.priority)
        return dict(db.session.execute(stmt).all())

    def total(self):
        return db.session.scalar(select(func.count(Task.id)))

    def todas(self):
        return db.session.scalars(select(Task)).all()

    def criadas_desde(self, momento):
        return db.session.scalar(
            select(func.count(Task.id)).where(Task.created_at >= momento)
        )

    def concluidas_desde(self, momento):
        return db.session.scalar(
            select(func.count(Task.id)).where(
                Task.status == 'done', Task.updated_at >= momento
            )
        )

    def salvar(self, task):
        db.session.add(task)
        db.session.commit()
        return task

    def remover(self, task):
        db.session.delete(task)
        db.session.commit()
