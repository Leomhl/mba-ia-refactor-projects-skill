"""Reports and categories controller."""
from flask import jsonify, request


class ReportController:
    def __init__(self, report_service, category_service):
        self.report_service = report_service
        self.category_service = category_service

    def resumo(self):
        return jsonify(self.report_service.resumo()), 200

    def por_usuario(self, user_id):
        return jsonify(self.report_service.por_usuario(user_id)), 200

    def listar_categorias(self):
        return jsonify(self.category_service.listar()), 200

    def criar_categoria(self):
        return jsonify(self.category_service.criar(request.get_json(silent=True))), 201

    def atualizar_categoria(self, cat_id):
        return jsonify(self.category_service.atualizar(cat_id, request.get_json(silent=True))), 200

    def remover_categoria(self, cat_id):
        self.category_service.remover(cat_id)
        return jsonify({'message': 'Categoria deletada'}), 200
