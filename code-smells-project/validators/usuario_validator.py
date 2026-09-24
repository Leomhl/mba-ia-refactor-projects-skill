"""User and login credential validation."""
from middlewares.error_handler import ValidationError

SENHA_MIN = 4


def validar_usuario(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")

    if "@" not in email:
        raise ValidationError("Email inválido")

    if len(senha) < SENHA_MIN:
        raise ValidationError(f"Senha deve ter no mínimo {SENHA_MIN} caracteres")

    return {"nome": nome, "email": email, "senha": senha}


def validar_credenciais(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    email = (dados.get("email") or "").strip()
    senha = dados.get("senha") or ""

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    return email, senha
