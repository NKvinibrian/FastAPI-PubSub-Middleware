"""
Observer Parser — Fidelize Funcional Wholesaler.

Converte dados do banco (pre_pedidos, pedidos, NFs) em
ObserverMessageSchema genéricos prontos para publicação.

Cada método:
  1. Consulta o banco (via SQLAlchemy session)
  2. Monta o payload no formato da VAN
  3. Envolve num ObserverMessageSchema com setup genérico
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas.vans.observer_message import (
    ObserverAction,
    ObserverMessageSchema,
    ObserverSetupSchema,
)
from app.infrastructure.db.models.vans.pre_pedidos import PrePedido, PrePedidoItem
from app.infrastructure.db.models.vans.pedidos import Pedido, PedidoItem, PedidoComplementoVans
from app.infrastructure.db.models.vans.notas_fiscais import NotaFiscal, NotaFiscalItem

logger = logging.getLogger(__name__)


# Mapeamento ObserverAction → nome no RequestDetails (campo name)
ACTION_TO_REQUEST_NAME: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "pedido_retorno",
    ObserverAction.ORDER_RETURN_REJECTION: "pedido_rejeicao",
    ObserverAction.RETURN_INVOICES: "nota_fiscal",
    ObserverAction.RETURN_CANCELLATION: "pedido_cancelamento",
}


class FidelizeObserverParser:
    """
    Parser do Observer para Fidelize Funcional Wholesaler.

    Consulta o banco e monta ObserverMessageSchema para os 4 fluxos.
    """

    def __init__(
        self,
        db: Session,
        origin_system: str,
        integration_id: int,
    ) -> None:
        self._db = db
        self._origin_system = origin_system
        self._integration_id = integration_id

    @staticmethod
    def _fmt_dt(dt: datetime | None) -> str:
        if not dt:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _make_message(
        self,
        action: ObserverAction,
        order_code: int | str,
        industry_code: str,
        payload: dict[str, Any],
    ) -> ObserverMessageSchema:
        """Helper: envolve um payload num ObserverMessageSchema genérico."""
        return ObserverMessageSchema(
            integration=self._origin_system,
            integration_id=self._integration_id,
            action=action,
            setup=ObserverSetupSchema(
                check_id="order_code",
                query_parameters={
                    "order_code": str(order_code),
                    "industry_code": industry_code,
                },
            ),
            payload=payload,
        )

    def _get_datasul_items(self, pre_pedido: PrePedido) -> dict[str, dict]:
        """
        Busca itens do Datasul (pedido confirmado) vinculados ao pré-pedido.

        Caminho: PrePedido.origem_sistema_id → PedidoComplementoVans.id_pedido_vans
                 → PedidoComplementoVans.id_pedido_datasul → Pedido → PedidoItem

        Returns:
            Dict com EAN como chave (via produto_id) e dados do item Datasul.
            Vazio se não encontrar vínculo.
        """
        complemento = self._db.scalars(
            select(PedidoComplementoVans).where(
                PedidoComplementoVans.id_pedido_vans == str(pre_pedido.origem_sistema_id),
                PedidoComplementoVans.origem_van == self._origin_system,
            )
        ).first()

        if not complemento:
            return {}

        pedido = self._db.scalars(
            select(Pedido).where(
                Pedido.id_pedido_datasul == complemento.id_pedido_datasul,
            )
        ).first()

        if not pedido:
            return {}

        pedido_itens = self._db.scalars(
            select(PedidoItem).where(PedidoItem.pedido_id == pedido.id)
        ).all()

        # Indexa por produto_id para cruzar com EAN do pré-pedido
        return {
            str(item.produto_id): {
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
                "percentual_desconto": item.percentual_desconto,
                "valor_desconto": item.valor_desconto,
                "motivo_atendimento": item.motivo_atendimento,
            }
            for item in pedido_itens
        }

    def _build_return_payload(
        self,
        pre_pedido: PrePedido,
        pre_pedido_itens: list[PrePedidoItem],
        reason: str,
    ) -> dict[str, Any]:
        """Monta payload de ORDER_RETURN ou ORDER_RETURN_REJECTION."""
        datasul_items = self._get_datasul_items(pre_pedido)

        products = []
        for item in pre_pedido_itens:
            ds = datasul_items.get(str(item.ean), {})
            products.append({
                "ean": item.ean,
                "response_amount": int(ds.get("quantidade", item.quantidade) or 0),
                "unit_discount_percentage": float(ds.get("percentual_desconto", item.desconto_percentual) or 0.0),
                "unit_discount_value": float(ds.get("valor_desconto", item.desconto_valor) or 0.0),
                "unit_net_value": float(item.valor_liquido or 0.0),
                "monitored": bool(item.produto_monitorado),
                "industry_consideration": ds.get("motivo_atendimento") or item.motivo_atendimento or "000",
            })

        return {
            "industry_code": pre_pedido.origem_industria_codigo or "",
            "order_code": pre_pedido.origem_sistema_id,
            "wholesaler_code": pre_pedido.distribuidor_cnpj or "",
            "wholesaler_order_code": pre_pedido.origem_industria_pedido_id,
            "payment_term": pre_pedido.prazo_negociado,
            "reason": reason,
            "processed_at": self._fmt_dt(datetime.now()),
            "invoice_at": None,
            "delivery_forecast_at": None,
            "products": products,
        }

    # ═══════════════════════════════════════════════════════════════════
    #  1. ORDER_RETURN — retorno de pedidos aceitos
    # ═══════════════════════════════════════════════════════════════════

    def parse_order_returns(self) -> list[ObserverMessageSchema]:
        """
        Monta mensagens de retorno de pedidos aceitos (createResponse).

        Query: pre_pedidos com erp_confirmed=True e vans_confirmed != True.
        """
        logger.debug("[FidelizeObserverParser] parse_order_returns")

        pre_pedidos = self._db.scalars(
            select(PrePedido).where(
                PrePedido.erp_confirmed == True,
                PrePedido.vans_confirmed != True,
                PrePedido.status == True,
            )
        ).all()

        messages = []
        for pp in pre_pedidos:
            itens = self._db.scalars(
                select(PrePedidoItem).where(PrePedidoItem.pre_pedido_id == pp.id)
            ).all()

            if not itens:
                logger.warning("[FidelizeObserverParser] PrePedido id=%d sem itens — pulando", pp.id)
                continue

            payload = self._build_return_payload(
                pre_pedido=pp,
                pre_pedido_itens=itens,
                reason="ORDER_SUCCESSFULLY_ACCEPTED",
            )

            msg = self._make_message(
                action=ObserverAction.ORDER_RETURN,
                order_code=pp.origem_sistema_id,
                industry_code=pp.origem_industria_codigo or "",
                payload=payload,
            )
            messages.append(msg)

        return messages

    # ═══════════════════════════════════════════════════════════════════
    #  2. ORDER_RETURN_REJECTION — retorno de pedidos rejeitados
    # ═══════════════════════════════════════════════════════════════════

    def parse_order_rejections(self) -> list[ObserverMessageSchema]:
        """
        Monta mensagens de rejeição (createResponse com reason rejeição).

        Query: pre_pedidos com erp_returned=True, vans_confirmed != True,
               e motivo_atendimento preenchido (indica rejeição).
        """
        logger.debug("[FidelizeObserverParser] parse_order_rejections")

        pre_pedidos = self._db.scalars(
            select(PrePedido).where(
                PrePedido.erp_returned == True,
                PrePedido.vans_confirmed != True,
                PrePedido.motivo_atendimento.isnot(None),
                PrePedido.status == True,
            )
        ).all()

        messages = []
        for pp in pre_pedidos:
            itens = self._db.scalars(
                select(PrePedidoItem).where(PrePedidoItem.pre_pedido_id == pp.id)
            ).all()

            if not itens:
                continue

            payload = self._build_return_payload(
                pre_pedido=pp,
                pre_pedido_itens=itens,
                reason="ORDER_REJECTED",
            )

            msg = self._make_message(
                action=ObserverAction.ORDER_RETURN_REJECTION,
                order_code=pp.origem_sistema_id,
                industry_code=pp.origem_industria_codigo or "",
                payload=payload,
            )
            messages.append(msg)

        return messages

    # ═══════════════════════════════════════════════════════════════════
    #  3. RETURN_INVOICES — notas fiscais
    # ═══════════════════════════════════════════════════════════════════

    def parse_invoices(self) -> list[ObserverMessageSchema]:
        """
        Monta mensagens de NFs (createInvoice).

        Query: pre_pedidos com nf_confirmed != True e status=True,
               cruzando com nota_fiscal via pedido_id.
        """
        logger.debug("[FidelizeObserverParser] parse_invoices")

        # Pre-pedidos pendentes de confirmação de NF
        pre_pedidos = self._db.scalars(
            select(PrePedido).where(
                PrePedido.erp_confirmed == True,
                PrePedido.nf_confirmed != True,
                PrePedido.status == True,
            )
        ).all()

        messages = []
        for pp in pre_pedidos:
            # Busca vínculo com Datasul
            complemento = self._db.scalars(
                select(PedidoComplementoVans).where(
                    PedidoComplementoVans.id_pedido_vans == str(pp.origem_sistema_id),
                    PedidoComplementoVans.origem_van == self._origin_system,
                )
            ).first()

            if not complemento:
                continue

            # Busca pedido Datasul
            pedido = self._db.scalars(
                select(Pedido).where(
                    Pedido.id_pedido_datasul == complemento.id_pedido_datasul,
                )
            ).first()

            if not pedido:
                continue

            # Busca NFs vinculadas ao pedido Datasul
            notas = self._db.scalars(
                select(NotaFiscal).where(
                    NotaFiscal.pedido_id == pedido.id,
                    NotaFiscal.status == True,
                )
            ).all()

            for nf in notas:
                nf_itens = self._db.scalars(
                    select(NotaFiscalItem).where(
                        NotaFiscalItem.notafiscal_id == nf.id
                    )
                ).all()

                products = [
                    {
                        "ean": item.ean or "",
                        "invoice_amount": int(item.quantidade or 0),
                        "unit_discount_percentage": float(item.valor_desconto or 0.0) / float(item.valor_bruto or 1.0) * 100 if item.valor_bruto else 0.0,
                        "unit_discount_value": float(item.valor_desconto or 0.0),
                        "unit_net_value": float(item.valor_liquido or 0.0),
                    }
                    for item in nf_itens
                ]

                payload = {
                    "industry_code": pp.origem_industria_codigo or "",
                    "order_code": pp.origem_sistema_id,
                    "wholesaler_code": pp.distribuidor_cnpj or "",
                    "customer_code": pp.cliente_cpf_cnpj or "",
                    "wholesaler_order_code": pp.origem_industria_pedido_id,
                    "processed_at": self._fmt_dt(datetime.now()),
                    "invoice_released_on": str(nf.data_emissao.date()) if nf.data_emissao else "",
                    "invoice_code": str(nf.numero),
                    "invoice_value": float(nf.valor_total_nota or 0.0),
                    "invoice_discount": float(nf.valor_desconto or 0.0),
                    "invoice_danfe_key": nf.chave_acesso or "",
                    "products": products,
                    "pre_pedido_id": pp.id,
                }

                msg = self._make_message(
                    action=ObserverAction.RETURN_INVOICES,
                    order_code=pp.origem_sistema_id,
                    industry_code=pp.origem_industria_codigo or "",
                    payload=payload,
                )
                messages.append(msg)

        return messages

    # ═══════════════════════════════════════════════════════════════════
    #  4. RETURN_CANCELLATION — cancelamentos
    # ═══════════════════════════════════════════════════════════════════

    def parse_cancellations(self) -> list[ObserverMessageSchema]:
        """
        Monta mensagens de cancelamento (createCancellation).

        Query: pre_pedidos com status=False e order_cancellation_sent != True.
        """
        logger.debug("[FidelizeObserverParser] parse_cancellations")

        pre_pedidos = self._db.scalars(
            select(PrePedido).where(
                PrePedido.status == False,
                PrePedido.order_cancellation_sent != True,
            )
        ).all()

        messages = []
        for pp in pre_pedidos:
            itens = self._db.scalars(
                select(PrePedidoItem).where(PrePedidoItem.pre_pedido_id == pp.id)
            ).all()

            if not itens:
                continue

            products = [{"ean": item.ean} for item in itens]

            payload = {
                "order_code": pp.origem_sistema_id,
                "industry_code": pp.origem_industria_codigo or "",
                "wholesaler_branch_code": pp.distribuidor_filial_cnpj or pp.distribuidor_cnpj or "",
                "products": products,
            }

            msg = self._make_message(
                action=ObserverAction.RETURN_CANCELLATION,
                order_code=pp.origem_sistema_id,
                industry_code=pp.origem_industria_codigo or "",
                payload=payload,
            )
            messages.append(msg)

        return messages
