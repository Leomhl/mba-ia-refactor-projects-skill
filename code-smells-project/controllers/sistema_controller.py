"""System routes: index, health check and administrative maintenance."""
import logging
import re
import sqlite3

from flask import jsonify, request

from config.settings import settings
from middlewares.error_handler import ForbiddenError, ValidationError

logger = logging.getLogger(__name__)


class SistemaController:
    # Row cap for the inspection query response.
    LIMITE_LINHAS_QUERY = 100

    def __init__(self, database, produto_model, usuario_model, pedido_model,
                 relatorio_service):
        self.database = database
        self.produto_model = produto_model
        self.usuario_model = usuario_model
        self.pedido_model = pedido_model
        self.relatorio_service = relatorio_service

    def index(self):
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": settings.VERSAO,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    def health(self):
        """Service availability.

        The original version returned SECRET_KEY, the database path, the debug
        flag and the environment label in this public payload — all removed.
        """
        self.database.connection().execute("SELECT 1")

        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self.produto_model.contar(),
                "usuarios": self.usuario_model.contar(),
                "pedidos": self.pedido_model.contar(),
            },
            "versao": settings.VERSAO,
        }), 200

    def relatorio_vendas(self):
        return jsonify({
            "dados": self.relatorio_service.vendas(),
            "sucesso": True,
        }), 200

    def reset_database(self):
        """Clears the tables. Requires an admin token and debug mode.

        The original endpoint verified nothing: any request wiped the
        database. Leaving the operation unprotected was CRITICAL finding
        AP-03.
        """
        self._exigir_admin()

        conexao = self.database.connection()
        cursor = conexao.cursor()
        try:
            cursor.execute("BEGIN")
            for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
                cursor.execute(f"DELETE FROM {tabela}")
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise

        logger.warning("admin.reset_db.executado")
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

    def executar_query(self):
        """Inspection query for local diagnostics.

        The original version forwarded any SQL from the request body straight
        to the database, without authentication, and committed write
        statements — arbitrary execution exposed over HTTP (AP-03). The
        endpoint remains so as not to break existing consumers, but under
        four restrictions:

        1. Only responds in development mode.
        2. Requires the X-Admin-Token header.
        3. Accepts SELECT only — no INSERT, UPDATE, DELETE, DROP, ATTACH or
           PRAGMA, so no write is ever committed.
        4. A single statement per request, with a row cap on the response.

        Restriction 4 is backed by the driver itself: sqlite3's
        `cursor.execute()` refuses more than one statement, which closes off
        semicolon statement stacking.
        """
        self._exigir_admin()

        dados = request.get_json(silent=True) or {}
        consulta = (dados.get("sql") or "").strip()

        if not consulta:
            raise ValidationError("Query não informada")

        self._exigir_somente_leitura(consulta)

        cursor = self.database.connection().cursor()
        try:
            cursor.execute(consulta)
        except sqlite3.Error as erro:
            # The driver message describes the query sent by the authenticated
            # administrator, not arbitrary internal structure.
            raise ValidationError(f"Query inválida: {erro}")

        linhas = cursor.fetchmany(self.LIMITE_LINHAS_QUERY)
        resultado = [dict(linha) for linha in linhas]

        logger.warning("admin.query.executada", extra={"linhas": len(resultado)})

        return jsonify({
            "dados": resultado,
            "total": len(resultado),
            "limite": self.LIMITE_LINHAS_QUERY,
            "sucesso": True,
        }), 200

    def _exigir_somente_leitura(self, consulta):
        sem_comentarios = re.sub(r"--[^\n]*|/\*.*?\*/", " ", consulta, flags=re.S).strip()

        if not sem_comentarios.lower().startswith(("select", "with")):
            raise ForbiddenError("Apenas consultas SELECT são permitidas")

        # Anything left after the first statement would be a second one;
        # the driver rejects those, and this check makes it explicit.
        corpo = sem_comentarios.rstrip().rstrip(";")
        if ";" in corpo:
            raise ForbiddenError("Apenas um comando por requisição")

        proibidos = (
            "attach", "detach", "pragma", "insert", "update", "delete",
            "drop", "alter", "create", "replace", "vacuum",
        )
        palavras = set(re.findall(r"[a-z_]+", corpo.lower()))
        encontrados = palavras.intersection(proibidos)
        if encontrados:
            raise ForbiddenError(
                "Comando não permitido: " + ", ".join(sorted(encontrados))
            )

    def _exigir_admin(self):
        if not settings.DEBUG:
            raise ForbiddenError("Operação disponível apenas em desenvolvimento")

        token = settings.ADMIN_TOKEN
        if not token:
            raise ForbiddenError("ADMIN_TOKEN não configurado")

        if request.headers.get("X-Admin-Token") != token:
            logger.warning("admin.acesso_negado")
            raise ForbiddenError("Token administrativo inválido")
