"""Composition root.

Schema creation left module level: importing `app` no longer creates a
database file as a side effect (playbook RP-01).
"""
from flask import Flask
from flask_cors import CORS

from config.settings import settings
from controllers.report_controller import ReportController
from controllers.sistema_controller import SistemaController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.error_handler import registrar_error_handlers
from repositories.category_repository import CategoryRepository
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from routes import report_routes, sistema_routes, task_routes, user_routes
from services.category_service import CategoryService
from services.report_service import ReportService
from services.task_service import TaskService
from services.user_service import UserService


def create_app(criar_schema=True):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['DEBUG'] = settings.DEBUG

    CORS(app, origins=settings.cors_origins)
    db.init_app(app)

    task_repository = TaskRepository()
    user_repository = UserRepository()
    category_repository = CategoryRepository()

    task_service = TaskService(task_repository, user_repository, category_repository)
    user_service = UserService(user_repository, task_repository)
    report_service = ReportService(task_repository, user_repository, category_repository)
    category_service = CategoryService(category_repository)

    app.register_blueprint(task_routes.criar_blueprint(TaskController(task_service)))
    app.register_blueprint(user_routes.criar_blueprint(UserController(user_service)))
    app.register_blueprint(
        report_routes.criar_blueprint(ReportController(report_service, category_service))
    )
    app.register_blueprint(sistema_routes.criar_blueprint(SistemaController()))

    registrar_error_handlers(app)

    if criar_schema:
        with app.app_context():
            db.create_all()

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
