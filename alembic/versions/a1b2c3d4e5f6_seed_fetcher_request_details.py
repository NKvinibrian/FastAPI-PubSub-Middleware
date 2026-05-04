"""Seed fetcher request_details rows

Cadastra as linhas de request_details usadas pelo fetcher do
Fidelize Funcional Wholesaler — endpoint, método e headers
para get_pre_orders e set_orders_as_imported.

Mesmo padrão das linhas já cadastradas para o Observer
(pedido_retorno, pedido_rejeicao, nota_fiscal, pedido_cancelamento).

Revision ID: a1b2c3d4e5f6
Revises: faa5329473ae
Create Date: 2026-05-04 00:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'faa5329473ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FIDELIZE_INTEGRATION_NAME = "Fidelize Funcional Wholesaler"

_ROWS = [
    {
        "id": "fidelize-wholesaler-get-pre-orders",
        "name": "get_pre_orders",
        "endpoint": "/",
        "request_method": "POST",
        "request_type": "GRAPHQL",
    },
    {
        "id": "fidelize-wholesaler-set-orders-as-imported",
        "name": "set_orders_as_imported",
        "endpoint": "/",
        "request_method": "POST",
        "request_type": "GRAPHQL",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    integration_id = bind.exec_driver_sql(
        "SELECT id FROM hub.integrations WHERE name = %s LIMIT 1",
        (_FIDELIZE_INTEGRATION_NAME,),
    ).scalar()

    if integration_id is None:
        # Sem a integração cadastrada não há o que semear.
        return

    for row in _ROWS:
        bind.exec_driver_sql(
            """
            INSERT INTO hub.request_details (
                id, integration_id, name, endpoint,
                request_method, request_type, headers, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, NULL, TRUE)
            ON CONFLICT (id) DO UPDATE SET
                integration_id = EXCLUDED.integration_id,
                name = EXCLUDED.name,
                endpoint = EXCLUDED.endpoint,
                request_method = EXCLUDED.request_method,
                request_type = EXCLUDED.request_type,
                status = TRUE
            """,
            (
                row["id"],
                integration_id,
                row["name"],
                row["endpoint"],
                row["request_method"],
                row["request_type"],
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for row in _ROWS:
        bind.exec_driver_sql(
            "DELETE FROM hub.request_details WHERE id = %s",
            (row["id"],),
        )
