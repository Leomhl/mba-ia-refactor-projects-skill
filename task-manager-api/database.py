from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def _ativar_foreign_keys(conexao, _registro):
    """Enables referential integrity checking in SQLite.

    SQLite keeps foreign keys disabled by default, so the constraints declared
    on the models were purely decorative — deleting a category left tasks
    pointing at a nonexistent id (playbook RP-09).
    """
    import sqlite3

    if isinstance(conexao, sqlite3.Connection):
        cursor = conexao.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
