"""Centralized error handling (playbook RP-11).

Replaces the 17 identical try/except blocks that returned `str(e)` to the
client. Technical detail goes to the log; the response carries a controlled
message.
"""
from flask import jsonify


class AppError(Exception):
    status_code = 500
    mensagem_padrao = "Erro interno"

    def __init__(self, mensagem=None):
        super().__init__(mensagem or self.mensagem_padrao)
        self.mensagem = mensagem or self.mensagem_padrao


class ValidationError(AppError):
    status_code = 400
    mensagem_padrao = "Dados inválidos"


class NotFoundError(AppError):
    status_code = 404
    mensagem_padrao = "Recurso não encontrado"


class UnauthorizedError(AppError):
    status_code = 401
    mensagem_padrao = "Credenciais inválidas"


class ForbiddenError(AppError):
    status_code = 403
    mensagem_padrao = "Acesso negado"


class ConflictError(AppError):
    status_code = 409
    mensagem_padrao = "Conflito de dados"


class EstoqueInsuficienteError(AppError):
    status_code = 400
    mensagem_padrao = "Estoque insuficiente"


def registrar_error_handlers(app):
    @app.errorhandler(AppError)
    def _app_error(erro):
        return jsonify({"erro": erro.mensagem, "sucesso": False}), erro.status_code

    @app.errorhandler(404)
    def _rota_inexistente(_erro):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro):
        return jsonify({"erro": "Método não permitido", "sucesso": False}), 405

    @app.errorhandler(Exception)
    def _erro_inesperado(erro):
        # The full exception stays in the server log, not in the response:
        # the SQLite message revealed table and column names.
        app.logger.exception("Erro não tratado: %s", type(erro).__name__)
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
