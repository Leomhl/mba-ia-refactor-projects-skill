from database import db
from models.user import agora, como_utc

STATUS_VALIDOS = ('pending', 'in_progress', 'done', 'cancelled')
STATUS_FINAIS = ('done', 'cancelled')
PRIORIDADE_MIN = 1
PRIORIDADE_MAX = 5
TITULO_MIN = 3
TITULO_MAX = 200


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(TITULO_MAX), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,
    )
    category_id = db.Column(
        db.Integer,
        # A removed category leaves the task unclassified, instead of
        # pointing at a nonexistent id (playbook RP-09).
        db.ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=agora)
    updated_at = db.Column(db.DateTime(timezone=True), default=agora, onupdate=agora)
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref=db.backref('tasks', passive_deletes=True))
    category = db.relationship('Category', backref=db.backref('tasks', passive_deletes=True))

    def to_dict(self, incluir_relacionados=False):
        """Single serialization for the task.

        The handlers built the dictionary field by field, with field sets that
        diverged between endpoints. The optional parameter covers the case
        where the user and category names are also expected.
        """
        dados = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
            'overdue': self.is_overdue(),
        }

        if incluir_relacionados:
            dados['user_name'] = self.user.name if self.user else None
            dados['category_name'] = self.category.name if self.category else None

        return dados

    def is_overdue(self):
        """Single source of truth for the overdue rule.

        The same condition was rewritten in five handlers, all of which
        ignored this method (playbook RP-13).
        """
        if not self.due_date:
            return False
        if self.status in STATUS_FINAIS:
            return False
        return como_utc(self.due_date) < agora()

    @staticmethod
    def validate_status(novo_status):
        return novo_status in STATUS_VALIDOS

    @staticmethod
    def validate_priority(prioridade):
        return PRIORIDADE_MIN <= prioridade <= PRIORIDADE_MAX
