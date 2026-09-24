"""System routes: index, health, report and maintenance."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint("sistema", __name__)

    bp.add_url_rule("/", "index", controller.index, methods=["GET"])
    bp.add_url_rule("/health", "health_check", controller.health, methods=["GET"])
    bp.add_url_rule(
        "/relatorios/vendas",
        "relatorio_vendas",
        controller.relatorio_vendas,
        methods=["GET"],
    )

    bp.add_url_rule(
        "/admin/query",
        "executar_query",
        controller.executar_query,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/admin/reset-db",
        "reset_database",
        controller.reset_database,
        methods=["POST"],
    )

    return bp
