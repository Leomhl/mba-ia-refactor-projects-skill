"""Report and category routes."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint('reports', __name__)

    bp.add_url_rule('/reports/summary', 'summary_report', controller.resumo, methods=['GET'])
    bp.add_url_rule(
        '/reports/user/<int:user_id>',
        'user_report',
        controller.por_usuario,
        methods=['GET'],
    )

    bp.add_url_rule('/categories', 'get_categories', controller.listar_categorias, methods=['GET'])
    bp.add_url_rule('/categories', 'create_category', controller.criar_categoria, methods=['POST'])
    bp.add_url_rule(
        '/categories/<int:cat_id>',
        'update_category',
        controller.atualizar_categoria,
        methods=['PUT'],
    )
    bp.add_url_rule(
        '/categories/<int:cat_id>',
        'delete_category',
        controller.remover_categoria,
        methods=['DELETE'],
    )

    return bp
