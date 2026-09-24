"""Product controller: translates HTTP into a domain call."""
from flask import jsonify, request

from middlewares.error_handler import NotFoundError
from validators.paginacao import parametros_de_pagina
from validators.produto_validator import validar_produto


class ProdutoController:
    def __init__(self, produto_model):
        self.produto_model = produto_model

    def listar(self):
        limite, offset = parametros_de_pagina()
        produtos = self.produto_model.listar(limite, offset)
        return jsonify({"dados": produtos, "sucesso": True}), 200

    def obter(self, id):
        produto = self.produto_model.obter(id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return jsonify({"dados": produto, "sucesso": True}), 200

    def criar(self):
        dados = validar_produto(request.get_json(silent=True))
        produto_id = self.produto_model.criar(**dados)
        return jsonify({
            "dados": {"id": produto_id},
            "sucesso": True,
            "mensagem": "Produto criado",
        }), 201

    def atualizar(self, id):
        if self.produto_model.obter(id) is None:
            raise NotFoundError("Produto não encontrado")

        dados = validar_produto(request.get_json(silent=True))
        self.produto_model.atualizar(id, **dados)
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    def deletar(self, id):
        if not self.produto_model.deletar(id):
            raise NotFoundError("Produto não encontrado")
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200

    def buscar(self):
        limite, offset = parametros_de_pagina()
        resultados = self.produto_model.buscar(
            termo=request.args.get("q", ""),
            categoria=request.args.get("categoria"),
            preco_min=_decimal_opcional("preco_min"),
            preco_max=_decimal_opcional("preco_max"),
            limite=limite,
            offset=offset,
        )
        return jsonify({
            "dados": resultados,
            "total": len(resultados),
            "sucesso": True,
        }), 200


def _decimal_opcional(nome):
    """Converts a numeric query string parameter, tolerating absence."""
    from middlewares.error_handler import ValidationError

    valor = request.args.get(nome)
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"{nome} deve ser numérico")
