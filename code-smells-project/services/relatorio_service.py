"""Sales report and discount policy.

The calculation lived inside the data access module, mixed with the queries.
The tiers became an iterable data structure (playbook RP-15).
"""

# Discount tiers over gross revenue, in descending threshold order. The
# first tier whose minimum is exceeded defines the rate.
FAIXAS_DESCONTO = (
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)


def calcular_desconto(faturamento):
    for minimo, taxa in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * taxa
    return 0


class RelatorioService:
    def __init__(self, database):
        self.database = database

    def vendas(self):
        cursor = self.database.connection().cursor()

        # The five separate COUNTs of the original code became one aggregation.
        cursor.execute(
            """
            SELECT COUNT(*)                                          AS total_pedidos,
                   COALESCE(SUM(total), 0)                           AS faturamento,
                   SUM(CASE WHEN status = 'pendente'  THEN 1 ELSE 0 END) AS pendentes,
                   SUM(CASE WHEN status = 'aprovado'  THEN 1 ELSE 0 END) AS aprovados,
                   SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END) AS cancelados
            FROM pedidos
            """
        )
        linha = cursor.fetchone()

        total_pedidos = linha["total_pedidos"]
        faturamento = linha["faturamento"] or 0
        desconto = calcular_desconto(faturamento)

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": linha["pendentes"] or 0,
            "pedidos_aprovados": linha["aprovados"] or 0,
            "pedidos_cancelados": linha["cancelados"] or 0,
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos else 0,
        }
