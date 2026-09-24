"""System routes."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint('sistema', __name__)

    bp.add_url_rule('/', 'index', controller.index, methods=['GET'])
    bp.add_url_rule('/health', 'health', controller.health, methods=['GET'])

    return bp
