"""User and authentication controller."""
from flask import jsonify, request

from validators import parametros_de_pagina


class UserController:
    def __init__(self, user_service):
        self.user_service = user_service

    def listar(self):
        limite, offset = parametros_de_pagina(request.args)
        return jsonify(self.user_service.listar(limite, offset)), 200

    def obter(self, user_id):
        limite, offset = parametros_de_pagina(request.args)
        return jsonify(self.user_service.obter(user_id, limite, offset)), 200

    def criar(self):
        return jsonify(self.user_service.criar(request.get_json(silent=True))), 201

    def atualizar(self, user_id):
        return jsonify(self.user_service.atualizar(user_id, request.get_json(silent=True))), 200

    def remover(self, user_id):
        self.user_service.remover(user_id)
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200

    def listar_tarefas(self, user_id):
        limite, offset = parametros_de_pagina(request.args)
        return jsonify(self.user_service.listar_tarefas(user_id, limite, offset)), 200

    def login(self):
        return jsonify(self.user_service.autenticar(request.get_json(silent=True))), 200
