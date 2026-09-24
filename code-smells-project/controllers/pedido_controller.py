"""Order controller. The checkout rule lives in PedidoService."""
from flask import jsonify, request

from validators.paginacao import parametros_de_pagina
from validators.pedido_validator import validar_pedido, validar_status


class PedidoController:
    def __init__(self, pedido_service):
        self.pedido_service = pedido_service

    def criar(self):
        usuario_id, itens = validar_pedido(request.get_json(silent=True))
        resultado = self.pedido_service.criar(usuario_id, itens)
        return jsonify({
            "dados": resultado,
            "sucesso": True,
            "mensagem": "Pedido criado com sucesso",
        }), 201

    def listar(self):
        limite, offset = parametros_de_pagina()
        return jsonify({
            "dados": self.pedido_service.listar(limite, offset),
            "sucesso": True,
        }), 200

    def listar_por_usuario(self, usuario_id):
        limite, offset = parametros_de_pagina()
        return jsonify({
            "dados": self.pedido_service.listar_por_usuario(usuario_id, limite, offset),
            "sucesso": True,
        }), 200

    def atualizar_status(self, pedido_id):
        status = validar_status(request.get_json(silent=True))
        self.pedido_service.atualizar_status(pedido_id, status)
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
