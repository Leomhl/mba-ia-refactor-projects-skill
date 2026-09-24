"""Product routes — path, method and handler only."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint("produtos", __name__)

    # The static route comes before the parameterized one: with a converter
    # looser than <int:>, /produtos/busca would be captured by /produtos/<id>.
    bp.add_url_rule("/produtos/busca", "buscar_produtos", controller.buscar, methods=["GET"])

    bp.add_url_rule("/produtos", "listar_produtos", controller.listar, methods=["GET"])
    bp.add_url_rule("/produtos", "criar_produto", controller.criar, methods=["POST"])
    bp.add_url_rule("/produtos/<int:id>", "buscar_produto", controller.obter, methods=["GET"])
    bp.add_url_rule("/produtos/<int:id>", "atualizar_produto", controller.atualizar, methods=["PUT"])
    bp.add_url_rule("/produtos/<int:id>", "deletar_produto", controller.deletar, methods=["DELETE"])

    return bp
