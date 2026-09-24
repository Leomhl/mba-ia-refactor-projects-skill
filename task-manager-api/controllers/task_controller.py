"""Task controller: receive, delegate, respond."""
from flask import jsonify, request

from validators import inteiro, parametros_de_pagina


class TaskController:
    def __init__(self, task_service):
        self.task_service = task_service

    def listar(self):
        limite, offset = parametros_de_pagina(request.args)
        return jsonify(self.task_service.listar(limite, offset)), 200

    def obter(self, task_id):
        return jsonify(self.task_service.obter(task_id)), 200

    def criar(self):
        return jsonify(self.task_service.criar(request.get_json(silent=True))), 201

    def atualizar(self, task_id):
        return jsonify(self.task_service.atualizar(task_id, request.get_json(silent=True))), 200

    def remover(self, task_id):
        self.task_service.remover(task_id)
        return jsonify({'message': 'Task deletada com sucesso'}), 200

    def buscar(self):
        limite, offset = parametros_de_pagina(request.args)

        prioridade = request.args.get('priority', '')
        user_id = request.args.get('user_id', '')

        filtros = {
            'termo': request.args.get('q', ''),
            'status': request.args.get('status', ''),
            'priority': inteiro(prioridade, 'priority') if prioridade else None,
            'user_id': inteiro(user_id, 'user_id') if user_id else None,
        }
        return jsonify(self.task_service.buscar(filtros, limite, offset)), 200

    def estatisticas(self):
        return jsonify(self.task_service.estatisticas()), 200
