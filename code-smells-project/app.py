"""Composition root.

Assembles the application: loads configuration, instantiates dependencies,
registers middlewares and routes. Declares no handlers and holds no business
rules.
"""
import logging

from flask import Flask
from flask_cors import CORS

from config.settings import settings
from controllers.pedido_controller import PedidoController
from controllers.produto_controller import ProdutoController
from controllers.sistema_controller import SistemaController
from controllers.usuario_controller import UsuarioController
from database import Database
from middlewares.error_handler import registrar_error_handlers
from models.pedido_model import PedidoModel
from models.produto_model import ProdutoModel
from models.usuario_model import UsuarioModel
from routes import pedido_routes, produto_routes, sistema_routes, usuario_routes
from services.notificacao_service import NotificacaoService
from services.pedido_service import PedidoService
from services.relatorio_service import RelatorioService


def create_app(database=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    CORS(app, origins=settings.cors_origins)

    # Data layer — injected, not imported as a global singleton.
    database = database or Database(settings.DB_PATH)
    database.init_schema()
    app.teardown_appcontext(database.close)

    produto_model = ProdutoModel(database)
    usuario_model = UsuarioModel(database)
    pedido_model = PedidoModel(database)

    notificacao_service = NotificacaoService()
    pedido_service = PedidoService(
        pedido_model, produto_model, usuario_model, notificacao_service
    )
    relatorio_service = RelatorioService(database)

    produto_controller = ProdutoController(produto_model)
    usuario_controller = UsuarioController(usuario_model)
    pedido_controller = PedidoController(pedido_service)
    sistema_controller = SistemaController(
        database, produto_model, usuario_model, pedido_model, relatorio_service
    )

    app.register_blueprint(produto_routes.criar_blueprint(produto_controller))
    app.register_blueprint(usuario_routes.criar_blueprint(usuario_controller))
    app.register_blueprint(pedido_routes.criar_blueprint(pedido_controller))
    app.register_blueprint(sistema_routes.criar_blueprint(sistema_controller))

    registrar_error_handlers(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
