"""Shared pagination for list endpoints (playbook RP-13).

The original listings returned the entire table, with no limit.
"""
from flask import request

from config.settings import settings
from middlewares.error_handler import ValidationError


def parametros_de_pagina():
    """Reads `limit` and `offset` from the query string, with a configurable cap."""
    limite = request.args.get("limit", settings.PAGE_SIZE_DEFAULT)
    offset = request.args.get("offset", 0)

    try:
        limite = int(limite)
        offset = int(offset)
    except (TypeError, ValueError):
        raise ValidationError("limit e offset devem ser inteiros")

    if limite < 1:
        raise ValidationError("limit deve ser maior que zero")
    if offset < 0:
        raise ValidationError("offset não pode ser negativo")

    return min(limite, settings.PAGE_SIZE_MAX), offset
