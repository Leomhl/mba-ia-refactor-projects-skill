"""Database connection and schema.

The connection is no longer a module singleton shared across threads
(playbook RP-05): each request gets its own, stored in the Flask context and
closed on teardown.
"""
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    estoque INTEGER NOT NULL DEFAULT 0,
    categoria TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    tipo TEXT DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    status TEXT NOT NULL DEFAULT 'pendente',
    total REAL NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pedidos_usuario ON pedidos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens_pedido(pedido_id);
CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria);
"""

PRODUTOS_INICIAIS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Sample passwords are hashed at load time (playbook RP-12). The credentials
# stay the same for anyone already using the API; what changes is what ends
# up stored in the column.
USUARIOS_INICIAIS = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


class Database:
    """Connection factory. Receives the path instead of reading a literal."""

    def __init__(self, path):
        self.path = path

    def connect(self):
        conexao = sqlite3.connect(self.path)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def connection(self):
        """Connection for the current request, created on demand."""
        if "db_conexao" not in g:
            g.db_conexao = self.connect()
        return g.db_conexao

    def close(self, _exc=None):
        conexao = g.pop("db_conexao", None)
        if conexao is not None:
            conexao.close()

    def init_schema(self):
        """Creates the tables and loads sample data into an empty database."""
        conexao = self.connect()
        try:
            conexao.executescript(SCHEMA)
            cursor = conexao.cursor()

            cursor.execute("SELECT COUNT(*) FROM produtos")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
                    " VALUES (?, ?, ?, ?, ?)",
                    PRODUTOS_INICIAIS,
                )

            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                    [
                        (nome, email, generate_password_hash(senha), tipo)
                        for nome, email, senha, tipo in USUARIOS_INICIAIS
                    ],
                )

            conexao.commit()
        finally:
            conexao.close()
