"""Order payload validation."""
from middlewares.error_handler import ValidationError
from models.pedido_model import STATUS_VALIDOS


def validar_pedido(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")

    itens = dados.get("itens") or []
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    normalizados = []
    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Item de pedido inválido")

        produto_id = item.get("produto_id")
        quantidade = item.get("quantidade")

        if not isinstance(produto_id, int):
            raise ValidationError("produto_id deve ser inteiro")
        if not isinstance(quantidade, int) or isinstance(quantidade, bool):
            raise ValidationError("quantidade deve ser inteira")
        if quantidade < 1:
            raise ValidationError("quantidade deve ser maior que zero")

        normalizados.append({"produto_id": produto_id, "quantidade": quantidade})

    return usuario_id, normalizados


def validar_status(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    status = dados.get("status", "")
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")

    return status
