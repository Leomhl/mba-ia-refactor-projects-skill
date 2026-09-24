"""Product data access.

Every query is parameterized (playbook RP-02). The model knows nothing about
`request` and returns no HTTP status codes.
"""

CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def _serializar(row):
    return {campo: row[campo] for campo in CAMPOS} if row else None


class ProdutoModel:
    def __init__(self, database):
        self.database = database

    def _cursor(self):
        return self.database.connection().cursor()

    def listar(self, limite, offset=0):
        cursor = self._cursor()
        cursor.execute(
            "SELECT * FROM produtos ORDER BY id LIMIT ? OFFSET ?",
            (limite, offset),
        )
        return [_serializar(row) for row in cursor.fetchall()]

    def obter(self, produto_id):
        cursor = self._cursor()
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return _serializar(cursor.fetchone())

    def criar(self, nome, descricao, preco, estoque, categoria):
        conexao = self.database.connection()
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
            " VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        conexao.commit()
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        conexao = self.database.connection()
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?,"
            " categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
        conexao.commit()
        return cursor.rowcount > 0

    def deletar(self, produto_id):
        conexao = self.database.connection()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conexao.commit()
        return cursor.rowcount > 0

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None,
               limite=50, offset=0):
        """Search with optional filters.

        The clause is built dynamically, but no value enters the SQL string —
        including the LIKE wildcards, which travel in the parameter.
        """
        sql = "SELECT * FROM produtos WHERE 1=1"
        parametros = []

        if termo:
            sql += " AND (nome LIKE ? OR descricao LIKE ?)"
            parametros.extend([f"%{termo}%", f"%{termo}%"])
        if categoria:
            sql += " AND categoria = ?"
            parametros.append(categoria)
        if preco_min is not None:
            sql += " AND preco >= ?"
            parametros.append(preco_min)
        if preco_max is not None:
            sql += " AND preco <= ?"
            parametros.append(preco_max)

        sql += " ORDER BY id LIMIT ? OFFSET ?"
        parametros.extend([limite, offset])

        cursor = self._cursor()
        cursor.execute(sql, parametros)
        return [_serializar(row) for row in cursor.fetchall()]

    def contar(self):
        cursor = self._cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM produtos")
        return cursor.fetchone()["total"]
