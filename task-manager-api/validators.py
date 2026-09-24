"""Input validation shared across controllers (playbook RP-13).

The same checks were rewritten in create_task, update_task, create_user,
update_user and, a sixth time, in utils/helpers.py — the last of which was
never called.
"""
import re
from datetime import datetime, timezone

from config.settings import settings
from middlewares.error_handler import ValidationError
from models.task import (PRIORIDADE_MAX, PRIORIDADE_MIN, STATUS_VALIDOS,
                         TITULO_MAX, TITULO_MIN)

ROLES_VALIDOS = ('user', 'admin', 'manager')
SENHA_MIN = 4
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')


def inteiro(valor, campo):
    """Converts to int, rejecting bool and non-numeric text.

    The original `priority < 1` comparisons raised TypeError when the client
    sent a string, resulting in a 500 instead of a 400.
    """
    if isinstance(valor, bool):
        raise ValidationError(f'{campo} deve ser um número inteiro')
    if isinstance(valor, int):
        return valor
    try:
        return int(str(valor))
    except (TypeError, ValueError):
        raise ValidationError(f'{campo} deve ser um número inteiro')


def validar_titulo(titulo):
    if not isinstance(titulo, str) or not titulo.strip():
        raise ValidationError('Título é obrigatório')

    titulo = titulo.strip()
    if len(titulo) < TITULO_MIN:
        raise ValidationError('Título muito curto')
    if len(titulo) > TITULO_MAX:
        raise ValidationError('Título muito longo')
    return titulo


def validar_status(status):
    if status not in STATUS_VALIDOS:
        raise ValidationError('Status inválido')
    return status


def validar_prioridade(valor):
    prioridade = inteiro(valor, 'Prioridade')
    if not PRIORIDADE_MIN <= prioridade <= PRIORIDADE_MAX:
        raise ValidationError(
            f'Prioridade deve ser entre {PRIORIDADE_MIN} e {PRIORIDADE_MAX}'
        )
    return prioridade


def validar_data(valor, mensagem='Formato de data inválido. Use YYYY-MM-DD'):
    if not valor:
        return None
    try:
        data = datetime.strptime(valor, '%Y-%m-%d')
    except (TypeError, ValueError):
        raise ValidationError(mensagem)
    return data.replace(tzinfo=timezone.utc)


def validar_email(email):
    if not email or not EMAIL_REGEX.match(email):
        raise ValidationError('Email inválido')
    return email


def validar_senha(senha):
    if not senha or len(senha) < SENHA_MIN:
        raise ValidationError(f'Senha deve ter no mínimo {SENHA_MIN} caracteres')
    return senha


def validar_role(role):
    if role not in ROLES_VALIDOS:
        raise ValidationError('Role inválido')
    return role


def normalizar_tags(tags):
    if tags is None:
        return None
    if isinstance(tags, list):
        return ','.join(str(t) for t in tags)
    return str(tags)


def parametros_de_pagina(args):
    """Optional pagination: without `limit`, the maximum cap applies.

    Keeping the default behavior avoids breaking clients that consume the
    whole listing, while still preventing an unbounded response.
    """
    limite = args.get('limit', settings.PAGE_SIZE_DEFAULT)
    offset = args.get('offset', 0)

    limite = inteiro(limite, 'limit')
    offset = inteiro(offset, 'offset')

    if limite < 1:
        raise ValidationError('limit deve ser maior que zero')
    if offset < 0:
        raise ValidationError('offset não pode ser negativo')

    return min(limite, settings.PAGE_SIZE_MAX), offset
