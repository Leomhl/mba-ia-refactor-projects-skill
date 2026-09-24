"""Product validation, shared between create and update.

The original code duplicated the block across both handlers, and the copies
had already diverged: PUT checked neither name length nor category
(playbook RP-13).
"""
from middlewares.error_handler import ValidationError

NOME_MIN = 2
NOME_MAX = 200
CATEGORIAS_VALIDAS = (
    "informatica", "moveis", "vestuario", "geral", "eletronicos", "livros",
)
CATEGORIA_PADRAO = "geral"
OBRIGATORIOS = ("nome", "preco", "estoque")


def _numero(valor, campo):
    """Accepts int/float, rejects bool and text.

    The original `preco < 0` comparison raised TypeError when the client sent
    a string, returning 500 where 400 was appropriate.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(f"{campo} deve ser numérico")
    return valor


def validar_produto(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    for campo in OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(f"{campo.capitalize()} é obrigatório")

    nome = dados["nome"]
    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    nome = nome.strip()

    if len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")

    preco = _numero(dados["preco"], "Preço")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")

    estoque = _numero(dados["estoque"], "Estoque")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")

    categoria = dados.get("categoria", CATEGORIA_PADRAO)
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(
            "Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS))
        )

    return {
        "nome": nome,
        "descricao": dados.get("descricao", ""),
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }
