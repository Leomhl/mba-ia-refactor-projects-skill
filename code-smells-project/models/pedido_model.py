"""Order data access.

Listings load items with a JOIN in two fixed queries, replacing the original
1 + N × 2 cascade (playbook RP-07).
"""
from collections import defaultdict

STATUS_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")


class PedidoModel:
    def __init__(self, database):
        self.database = database

    def _cursor(self):
        return self.database.connection().cursor()

    def _montar(self, pedidos):
        """Attaches items to orders with a single extra query."""
        if not pedidos:
            return []

        ids = [pedido["id"] for pedido in pedidos]
        marcadores = ",".join("?" * len(ids))

        cursor = self._cursor()
        cursor.execute(
            f"""
            SELECT i.pedido_id,
                   i.produto_id,
                   i.quantidade,
                   i.preco_unitario,
                   p.nome AS produto_nome
            FROM itens_pedido i
            LEFT JOIN produtos p ON p.id = i.produto_id
            WHERE i.pedido_id IN ({marcadores})
            ORDER BY i.id
            """,
            ids,
        )

        itens_por_pedido = defaultdict(list)
        for item in cursor.fetchall():
            itens_por_pedido[item["pedido_id"]].append({
                "produto_id": item["produto_id"],
                "produto_nome": item["produto_nome"] or "Desconhecido",
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            })

        return [
            {
                "id": pedido["id"],
                "usuario_id": pedido["usuario_id"],
                "status": pedido["status"],
                "total": pedido["total"],
                "criado_em": pedido["criado_em"],
                "itens": itens_por_pedido.get(pedido["id"], []),
            }
            for pedido in pedidos
        ]

    def listar(self, limite, offset=0):
        cursor = self._cursor()
        cursor.execute(
            "SELECT * FROM pedidos ORDER BY id LIMIT ? OFFSET ?",
            (limite, offset),
        )
        return self._montar(cursor.fetchall())

    def listar_por_usuario(self, usuario_id, limite, offset=0):
        cursor = self._cursor()
        cursor.execute(
            "SELECT * FROM pedidos WHERE usuario_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (usuario_id, limite, offset),
        )
        return self._montar(cursor.fetchall())

    def obter(self, pedido_id):
        cursor = self._cursor()
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._montar([row])[0]

    def atualizar_status(self, pedido_id, status):
        conexao = self.database.connection()
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?",
            (status, pedido_id),
        )
        conexao.commit()
        return cursor.rowcount > 0

    def contar(self):
        cursor = self._cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM pedidos")
        return cursor.fetchone()["total"]

    # ------------------------------------------------------------------
    # Transactional operations used by PedidoService
    # ------------------------------------------------------------------

    def obter_precos(self, produto_ids):
        """Price, name and stock for the given products, in one query."""
        if not produto_ids:
            return {}

        marcadores = ",".join("?" * len(produto_ids))
        cursor = self._cursor()
        cursor.execute(
            f"SELECT id, nome, preco, estoque FROM produtos WHERE id IN ({marcadores})",
            list(produto_ids),
        )
        return {row["id"]: dict(row) for row in cursor.fetchall()}

    def registrar(self, usuario_id, itens, total):
        """Writes order, items and stock decrement in a single transaction.

        The stock condition lives inside the UPDATE itself: two concurrent
        requests for the last unit cannot both succeed (playbook RP-08).

        Returns the order id, or raises EstoqueInsuficienteError.
        """
        from middlewares.error_handler import EstoqueInsuficienteError

        conexao = self.database.connection()
        cursor = conexao.cursor()
        try:
            cursor.execute("BEGIN")
            cursor.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
                (usuario_id, total),
            )
            pedido_id = cursor.lastrowid

            for item in itens:
                cursor.execute(
                    "UPDATE produtos SET estoque = estoque - ?"
                    " WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if cursor.rowcount == 0:
                    raise EstoqueInsuficienteError(
                        f"Estoque insuficiente para {item['produto_nome']}"
                    )

                cursor.execute(
                    "INSERT INTO itens_pedido"
                    " (pedido_id, produto_id, quantidade, preco_unitario)"
                    " VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], item["preco"]),
                )

            conexao.commit()
            return pedido_id
        except Exception:
            conexao.rollback()
            raise
