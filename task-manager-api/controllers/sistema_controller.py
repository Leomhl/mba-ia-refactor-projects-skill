"""System routes."""
from flask import jsonify

from config.settings import settings
from models.user import agora


class SistemaController:
    def index(self):
        return jsonify({'message': 'Task Manager API', 'version': settings.VERSAO})

    def health(self):
        return jsonify({'status': 'ok', 'timestamp': str(agora())})
