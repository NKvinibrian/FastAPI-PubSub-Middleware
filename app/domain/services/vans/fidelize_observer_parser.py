"""
Observer Parser — Fidelize Funcional Wholesaler.

Converte dados do banco (pre_pedidos, pedidos, NFs) em
ObserverMessageSchema genéricos prontos para publicação.

Nenhum acesso direto ao banco — todas as consultas passam pelo
ObserverQueryRepository (adaptado do ObserverBase legado).

Cada método:
  1. Consulta via repositório
  2. Monta o payload no formato da VAN
  3. Envolve num ObserverMessageSchema com setup genérico
"""

import logging
from datetime import datetime
from typing import Any

from app.api.v1.schemas.vans.observer_message import (
    ObserverAction,
    ObserverMessageSchema,
    ObserverSetupSchema,
)
from app.domain.entities.vans.pedidos import PedidoEntity, PedidoItemEntity
from app.domain.entities.vans.pre_pedidos import PrePedidoEntity, PrePedidoItemEntity
from app.domain.protocol.vans.observer_query_repository import (
    ObserverQueryRepositoryProtocol,
)

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

    Recebe dados via ObserverQueryRepository e monta
    ObserverMessageSchema para os 4 fluxos.

    Args:
        observer_repo: Repositório de queries cross-table do Observer.
        origin_system: Nome da integração (ex: "Fidelize Funcional Wholesaler").
        integration_id: ID da integração no banco.
        include_rejected_items: Quando True (padrão), inclui na lista de produtos
            todos os itens do pre_pedido, mesmo os que foram rejeitados no Datasul.
    """

    def __init__(
        self,
        observer_repo: ObserverQueryRepositoryProtocol,
        origin_system: str,
        integration_id: int,
        include_rejected_items: bool = True,
    ) -> None:
        self._repo = observer_repo
        self._origin_system = origin_system
        self._integration_id = integration_id
        self._include_rejected_items = include_rejected_items

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

    def _build_return_payload(
        self,
        pre_pedido: PrePedidoEntity,
        pre_pedido_itens: list[PrePedidoItemEntity],
        reason: str,
        pedido: PedidoEntity | None = None,
        pedido_itens: list[PedidoItemEntity] | None = None,
    ) -> dict[str, Any]:
        """
        Monta payload de ORDER_RETURN ou ORDER_RETURN_REJECTION.

        Se pedido_itens disponível e reason == ORDER_SUCCESSFULLY_ACCEPTED,
        detecta aceitação parcial verificando se algum PedidoItem.status=False.
        """
        pedido_itens = pedido_itens or []

        # Detecta aceitação parcial somente no fluxo de aceitação
        if reason == "ORDER_SUCCESSFULLY_ACCEPTED" and pedido_itens:
            rejected = [i for i in pedido_itens if i.status is False]
            if rejected:
                reason = "ORDER_PARTIALLY_ACCEPTED"

        products = []
        for item in pre_pedido_itens:
            products.append({
                "ean": item.ean,
                "response_amount": int(item.quantidade or 0),
                "unit_discount_percentage": float(item.desconto_percentual or 0.0),
                "unit_discount_value": float(item.desconto_valor or 0.0),
                "unit_net_value": float(item.valor_liquido or 0.0),
                "monitored": bool(item.produto_monitorado),
                "industry_consideration": item.motivo_atendimento or "000",
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
            "pre_pedido_id": pre_pedido.id,
            "pedido_datasul_id": pedido.id_pedido_datasul if pedido else None,
        }

    # ═══════════════════════════════════════════════════════════════════
    #  1. ORDER_RETURN — retorno de pedidos aceitos
    # ═══════════════════════════════════════════════════════════════════

    def parse_order_returns(self) -> list[ObserverMessageSchema]:
        """
        Monta mensagens de retorno de pedidos aceitos (createResponse).

        Query via ObserverQueryRepository:
            PrePedido → ComplementoVans → Pedido
            WHERE descricao_etapa IN ('Pedido Efetivado', 'Pedido Aprovado Crédito')
                  AND vans_confirmed IS NOT True
        """
        logger.debug("[FidelizeObserverParser] parse_order_returns")

        pre_pedidos = self._repo.get_pre_pedidos_for_order_return(self._origin_system)

        messages = []
        for pp in pre_pedidos:
            itens = self._repo.get_pre_pedido_itens(pp.id)

            if not itens:
                logger.warning("[FidelizeObserverParser] PrePedido id=%d sem itens — pulando", pp.id)
                continue

            pedido, pedido_itens = self._repo.get_pedido_data(
                pp.origem_sistema_id, self._origin_system,
            )

            payload = self._build_return_payload(
                pre_pedido=pp,
                pre_pedido_itens=itens,
                reason="ORDER_SUCCESSFULLY_ACCEPTED",
                pedido=pedido,
                pedido_itens=pedido_itens,
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

        Query via ObserverQueryRepository:
            PrePedido → ComplementoVans → Pedido
            WHERE descricao_etapa IN ('Pedido Cancelado')
                  AND vans_confirmed IS NOT True
        """
        logger.debug("[FidelizeObserverParser] parse_order_rejections")

        pre_pedidos = self._repo.get_pre_pedidos_for_rejection(self._origin_system)

        messages = []
        for pp in pre_pedidos:
            itens = self._repo.get_pre_pedido_itens(pp.id)

            if not itens:
                continue

            pedido, pedido_itens = self._repo.get_pedido_data(
                pp.origem_sistema_id, self._origin_system,
            )

            payload = self._build_return_payload(
                pre_pedido=pp,
                pre_pedido_itens=itens,
                reason="ORDER_REJECTED",
                pedido=pedido,
                pedido_itens=pedido_itens,
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

        Query via ObserverQueryRepository:
            PrePedido → ComplementoVans → Pedido
            WHERE descricao_etapa IN ('Pedido Efetivado', 'Pedido Aprovado Crédito')
                  AND nf_confirmed IS NOT True
        """
        logger.debug("[FidelizeObserverParser] parse_invoices")

        pre_pedidos = self._repo.get_pre_pedidos_for_invoice(self._origin_system)

        messages = []
        for pp in pre_pedidos:
            notas = self._repo.get_notas_fiscais_for_pre_pedido(
                pp.origem_sistema_id, self._origin_system,
            )

            for nf in notas:
                nf_itens = self._repo.get_nota_fiscal_itens(nf.id)

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

        Query via ObserverQueryRepository:
            PrePedido → ComplementoVans → Pedido
            WHERE descricao_etapa IN ('Pedido Cancelado')
                  AND vans_confirmed IS True (já retornado)
                  AND order_cancellation_sent IS NOT True
        """
        logger.debug("[FidelizeObserverParser] parse_cancellations")

        pre_pedidos = self._repo.get_pre_pedidos_for_cancellation(self._origin_system)

        messages = []
        for pp in pre_pedidos:
            itens = self._repo.get_pre_pedido_itens(pp.id)

            if not itens:
                continue

            products = [{"ean": item.ean} for item in itens]

            payload = {
                "order_code": pp.origem_sistema_id,
                "industry_code": pp.origem_industria_codigo or "",
                "wholesaler_branch_code": pp.distribuidor_filial_cnpj or pp.distribuidor_cnpj or "",
                "products": products,
                "pre_pedido_id": pp.id,
            }

            msg = self._make_message(
                action=ObserverAction.RETURN_CANCELLATION,
                order_code=pp.origem_sistema_id,
                industry_code=pp.origem_industria_codigo or "",
                payload=payload,
            )
            messages.append(msg)

        return messages
