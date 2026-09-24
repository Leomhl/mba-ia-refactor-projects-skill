"""Centralized error handling (playbook RP-11).

Replaces the nine bare `except:` blocks, which swallowed any exception and
returned the same generic message without recording anything.
"""
from flask import jsonify


class AppError(Exception):
    status_code = 500
    mensagem_padrao = 'Erro interno'

    def __init__(self, mensagem=None):
        super().__init__(mensagem or self.mensagem_padrao)
        self.mensagem = mensagem or self.mensagem_padrao


class ValidationError(AppError):
    status_code = 400
    mensagem_padrao = 'Dados inválidos'


class NotFoundError(AppError):
    status_code = 404
    mensagem_padrao = 'Recurso não encontrado'


class UnauthorizedError(AppError):
    status_code = 401
    mensagem_padrao = 'Credenciais inválidas'


class ForbiddenError(AppError):
    status_code = 403
    mensagem_padrao = 'Acesso negado'


class ConflictError(AppError):
    status_code = 409
    mensagem_padrao = 'Conflito de dados'


def registrar_error_handlers(app):
    from database import db

    @app.errorhandler(AppError)
    def _app_error(erro):
        return jsonify({'error': erro.mensagem}), erro.status_code

    @app.errorhandler(404)
    def _rota_inexistente(_erro):
        return jsonify({'error': 'Recurso não encontrado'}), 404

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro):
        return jsonify({'error': 'Método não permitido'}), 405

    @app.errorhandler(Exception)
    def _erro_inesperado(erro):
        # The session must be discarded: leaving it dirty propagates the
        # error to the next request that reuses the connection.
        db.session.rollback()
        app.logger.exception('Erro não tratado: %s', type(erro).__name__)
        return jsonify({'error': 'Erro interno'}), 500
