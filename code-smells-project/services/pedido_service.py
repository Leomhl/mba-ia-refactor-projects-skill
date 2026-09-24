"""Order business rules.

Checkout spans product, order, item and stock — exactly the case where a
Service layer is justified (architecture guidelines).
"""
from middlewares.error_handler import NotFoundError, ValidationError


class PedidoService:
    def __init__(self, pedido_model, produto_model, usuario_model, notificacao_service):
        self.pedido_model = pedido_model
        self.produto_model = produto_model
        self.usuario_model = usuario_model
        self.notificacao_service = notificacao_service

    def criar(self, usuario_id, itens):
        if self.usuario_model.obter(usuario_id) is None:
            raise NotFoundError("Usuário não encontrado")

        # One query for all products in the order, instead of one per item.
        produtos = self.pedido_model.obter_precos({item["produto_id"] for item in itens})

        detalhados = []
        total = 0.0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise ValidationError(f"Produto {item['produto_id']} não encontrado")

            total += produto["preco"] * item["quantidade"]
            detalhados.append({
                "produto_id": produto["id"],
                "produto_nome": produto["nome"],
                "preco": produto["preco"],
                "quantidade": item["quantidade"],
            })

        # The stock check happens inside the transaction, alongside the decrement.
        pedido_id = self.pedido_model.registrar(usuario_id, detalhados, round(total, 2))

        self.notificacao_service.pedido_criado(pedido_id, usuario_id)

        return {"pedido_id": pedido_id, "total": round(total, 2)}

    def listar(self, limite, offset):
        return self.pedido_model.listar(limite, offset)

    def listar_por_usuario(self, usuario_id, limite, offset):
        return self.pedido_model.listar_por_usuario(usuario_id, limite, offset)

    def atualizar_status(self, pedido_id, status):
        if not self.pedido_model.atualizar_status(pedido_id, status):
            raise NotFoundError("Pedido não encontrado")

        self.notificacao_service.status_alterado(pedido_id, status)
