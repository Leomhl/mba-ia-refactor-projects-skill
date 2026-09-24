"""User and authentication controller."""
import logging

from flask import jsonify, request

from middlewares.error_handler import ConflictError, NotFoundError, UnauthorizedError
from validators.paginacao import parametros_de_pagina
from validators.usuario_validator import validar_credenciais, validar_usuario

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model):
        self.usuario_model = usuario_model

    def listar(self):
        limite, offset = parametros_de_pagina()
        usuarios = self.usuario_model.listar(limite, offset)
        return jsonify({"dados": usuarios, "sucesso": True}), 200

    def obter(self, id):
        usuario = self.usuario_model.obter(id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return jsonify({"dados": usuario, "sucesso": True}), 200

    def criar(self):
        dados = validar_usuario(request.get_json(silent=True))

        if self.usuario_model.obter_por_email(dados["email"]) is not None:
            raise ConflictError("Email já cadastrado")

        usuario_id = self.usuario_model.criar(**dados)
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    def login(self):
        email, senha = validar_credenciais(request.get_json(silent=True))
        usuario = self.usuario_model.autenticar(email, senha)

        if usuario is None:
            # No email in the log: user identifiers do not go to stdout.
            logger.warning("login.falha")
            raise UnauthorizedError("Email ou senha inválidos")

        logger.info("login.sucesso", extra={"usuario_id": usuario["id"]})
        return jsonify({
            "dados": usuario,
            "sucesso": True,
            "mensagem": "Login OK",
        }), 200
