"""
Mock do serviço Datasul para testes.

Além de simular autenticação e aceitação de pedidos, este mock
persiste os dados como se o Datasul tivesse processado e devolvido
o pedido — criando Pedido, PedidoItem e PedidoComplementoVans no banco.

Isso permite que o Observer parser encontre os dados ao consultar
a relação pre_pedido ↔ pedido nos fluxos de retorno.

Campos alinhados com os pedidos reais de produção:
    - origem          = "datasul"
    - pedido_tipo     = 3
    - base_origem     = 0
    - condicao_pagamento = 0
    - codigo_etapa    = 1
    - descricao_etapa = "Pedido Aprovado Crédito"
    - id_pedido_datasul = hash(order_code) no range 100_000–999_999
      (evita colisão com IDs reais que ficam em torno de 80K–90K)
"""

import logging
from datetime import date, datetime

from app.domain.protocol.datasul.datasul import DatasulProtocol

logger = logging.getLogger(__name__)

# Range de IDs mock: acima dos IDs reais do Datasul (~80K–90K em produção)
_MOCK_ID_BASE = 100_000
_MOCK_ID_RANGE = 900_000


class MockDatasulService(DatasulProtocol):
    """
    Mock do Datasul para testes.

    Simula o fluxo completo de aceite:
        1. login → token fictício
        2. send_pre_pedido → persiste Pedido + PedidoItem + PedidoComplementoVans
           e retorna True (aceito)

    id_pedido_datasul é derivado por hash do order_code no range 100K–999K.
    A operação é idempotente: se o complemento já existe, não recria.
    """

    def login(self, username: str, password: str) -> str:
        return "Datasul Mock Token"

    def send_pre_pedido(self, token: str, data: dict) -> bool:
        """
        Simula aceitação pelo Datasul e salva os dados no banco.

        Cria Pedido + PedidoItem + PedidoComplementoVans para que o
        FidelizeObserverParser encontre a relação ao processar os retornos.
        """
        try:
            self._simulate_datasul_return(data)
        except Exception:
            logger.exception(
                "[MOCK-DATASUL] ❌ Falha ao simular retorno Datasul | order_code=%s",
                data.get("order_code"),
            )
            # Ainda retorna True — o subscriber marca erp_confirmed mesmo se a
            # simulação falhar (ex: já existe no banco).
        return True

    @staticmethod
    def _datasul_id_for(order_code: str) -> int:
        """
        Gera id_pedido_datasul mock estável para o order_code.

        Range: 100_000–999_999 (acima dos IDs reais de produção ~80K–90K).
        """
        return abs(hash(order_code)) % _MOCK_ID_RANGE + _MOCK_ID_BASE

    @staticmethod
    def _simulate_datasul_return(data: dict) -> None:
        """
        Persiste Pedido, PedidoItem e PedidoComplementoVans no banco.

        Idempotente: verifica PedidoComplementoVans antes de criar.
        """
        from sqlalchemy import select

        from app.infrastructure.db import SessionLocal
        from app.infrastructure.db.models.vans.pedidos import (
            Pedido,
            PedidoComplementoVans,
            PedidoItem,
        )

        order_code = str(data.get("order_code", ""))
        origin_system = data.get("origin_system", "")
        products = data.get("products", [])
        datasul_id = MockDatasulService._datasul_id_for(order_code)

        # Calcula valor total dos itens para preencher valor_pedido / valor_bruto
        valor_bruto = sum(
            float(p.get("gross_value") or p.get("net_value") or 0) * int(p.get("amount") or 0)
            for p in products
        )

        db = SessionLocal()
        try:
            # Idempotência: se o complemento já existe, não recria
            existing = db.scalars(
                select(PedidoComplementoVans).where(
                    PedidoComplementoVans.id_pedido_vans == order_code,
                    PedidoComplementoVans.origem_van == origin_system,
                )
            ).first()

            if existing:
                logger.debug(
                    "[MOCK-DATASUL] Pedido já simulado | order_code=%s — ignorando",
                    order_code,
                )
                return

            now = datetime.now()

            # Cria Pedido (campos espelhando o padrão de produção)
            pedido = Pedido(
                id_pedido_datasul=datasul_id,
                origem="datasul",
                filial_cnpj=(
                    data.get("wholesaler_branch_code")
                    or data.get("wholesaler_code")
                    or "00000000000000"
                ),
                filial_id="10001",
                data_emissao=date.today(),
                pedido_tipo=3,
                condicao_pagamento=0,
                obs="",
                pedido_num=0,
                valor_pedido=valor_bruto,
                valor_bruto=valor_bruto,
                percentual_desconto=0.0,
                valor_desconto=0.0,
                cliente_id=data.get("customer_code") or "MOCK",
                entidade_tipo=1,
                base_origem=0,
                codigo_etapa=1,
                descricao_etapa="Pedido Aprovado Crédito",
                data_etapa=now,
                is_pbm=False,
            )
            db.add(pedido)
            db.flush()  # obtém pedido.id sem commit

            # Cria PedidoItems (produto_id = índice sequencial — sem mapeamento EAN ainda)
            for i, product in enumerate(products):
                item = PedidoItem(
                    id_pedido_datasul=datasul_id,
                    sequencia_id=i + 1,
                    pedido_id=pedido.id,
                    produto_id=i + 1,
                    quantidade=float(product.get("amount") or 0),
                    valor_unitario=float(product.get("net_value") or 0.0),
                    percentual_desconto=float(product.get("discount_percentage") or 0.0),
                    valor_desconto=0.0,
                    status=True,
                )
                db.add(item)

            # Cria PedidoComplementoVans — vínculo entre order_code VAN e id Datasul
            complemento = PedidoComplementoVans(
                id_pedido_datasul=datasul_id,
                id_pedido_vans=order_code,
                origem_van=origin_system,
                status_atual="ACCEPTED",
                is_finished=False,
            )
            db.add(complemento)
            db.commit()

            logger.info(
                "[MOCK-DATASUL] ✔ Pedido simulado | order_code=%s | datasul_id=%d | itens=%d",
                order_code,
                datasul_id,
                len(products),
            )

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()