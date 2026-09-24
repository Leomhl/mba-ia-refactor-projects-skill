"""User data access and credential verification.

The `senha` field never leaves this module: the public serialization does not
include it (playbook RP-12).
"""
from werkzeug.security import check_password_hash, generate_password_hash

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")


def _serializar(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS} if row else None


class UsuarioModel:
    def __init__(self, database):
        self.database = database

    def _cursor(self):
        return self.database.connection().cursor()

    def listar(self, limite, offset=0):
        cursor = self._cursor()
        cursor.execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios"
            " ORDER BY id LIMIT ? OFFSET ?",
            (limite, offset),
        )
        return [_serializar(row) for row in cursor.fetchall()]

    def obter(self, usuario_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,),
        )
        return _serializar(cursor.fetchone())

    def obter_por_email(self, email):
        cursor = self._cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        return cursor.fetchone()

    def criar(self, nome, email, senha, tipo="cliente"):
        conexao = self.database.connection()
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
        conexao.commit()
        return cursor.lastrowid

    def autenticar(self, email, senha):
        """Verifies the credential and returns public data, or None.

        The password is compared in memory against the hash — it is no longer
        a WHERE criterion, which was the login injection vector.
        """
        row = self.obter_por_email(email)
        if row is None:
            return None

        armazenada = row["senha"]

        if check_password_hash(armazenada, senha):
            return _serializar(row)

        # Databases created before this fix stored the password in plaintext.
        # When it matches, the record is upgraded to a hash during login —
        # a transparent migration that does not force a password reset.
        if armazenada == senha:
            self._regravar_hash(row["id"], senha)
            return _serializar(row)

        return None

    def _regravar_hash(self, usuario_id, senha):
        conexao = self.database.connection()
        conexao.execute(
            "UPDATE usuarios SET senha = ? WHERE id = ?",
            (generate_password_hash(senha), usuario_id),
        )
        conexao.commit()

    def contar(self):
        cursor = self._cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        return cursor.fetchone()["total"]
