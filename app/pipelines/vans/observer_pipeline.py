"""
Pipeline genérica do Observer para VANs.

Encapsula o fluxo reverso: Query DB → Parse → Publish.

Executa os 4 fluxos do Observer em sequência:
    1. ORDER_RETURN       — retorno de pedidos aceitos
    2. ORDER_RETURN_REJECTION — retorno de pedidos rejeitados
    3. RETURN_CANCELLATION — cancelamentos
    4. RETURN_INVOICES    — notas fiscais

Cada fluxo:
    - Chama o parser correspondente
    - Se houver mensagens, publica no PubSub
    - Registra logs via IntegrationLogger
"""

import logging
from uuid import UUID

from app.api.v1.schemas.vans.observer_message import ObserverAction
from app.domain.protocol.vans.observer_parser import ObserverParserProtocol
from app.domain.services.vans.integration_logger import IntegrationLogger
from app.infrastructure.vans.pubsub.observer_publisher import ObserverPubSubPublisher

logger = logging.getLogger(__name__)

_SEPARATOR = "─" * 60

# Ordem de execução dos fluxos (mesma do observer antigo)
_FLOW_ORDER: list[tuple[ObserverAction, str]] = [
    (ObserverAction.ORDER_RETURN, "parse_order_returns"),
    (ObserverAction.ORDER_RETURN_REJECTION, "parse_order_rejections"),
    (ObserverAction.RETURN_CANCELLATION, "parse_cancellations"),
    (ObserverAction.RETURN_INVOICES, "parse_invoices"),
]


class ObserverPipeline:
    """
    Orquestrador genérico do Observer.

    Para cada fluxo (action), chama o parser correspondente
    e publica as mensagens no PubSub.

    Attributes:
        _parser:             Parser do Observer (ObserverParserProtocol).
        _publisher:          Publisher genérico do Observer.
        _integration_logger: Helper de logging por etapa.
        _log_uuid:           UUID do grupo de processamento.
    """

    def __init__(
        self,
        parser: ObserverParserProtocol,
        publisher: ObserverPubSubPublisher,
        integration_logger: IntegrationLogger,
        log_uuid: UUID,
    ) -> None:
        self._parser = parser
        self._publisher = publisher
        self._integration_logger = integration_logger
        self._log_uuid = log_uuid

    async def run(self) -> None:
        """Executa os 4 fluxos do Observer em sequência."""
        logger.info(_SEPARATOR)
        logger.info("🔭 ObserverPipeline STARTED | log_uuid=%s", self._log_uuid)
        logger.info(_SEPARATOR)

        for action, method_name in _FLOW_ORDER:
            await self._process_flow(action, method_name)

        logger.info(_SEPARATOR)
        logger.info("✅ ObserverPipeline FINISHED | log_uuid=%s", self._log_uuid)
        logger.info(_SEPARATOR)

    async def _process_flow(self, action: ObserverAction, method_name: str) -> None:
        """
        Processa um único fluxo do Observer.

        Args:
            action: Tipo da ação (ex: ORDER_RETURN).
            method_name: Nome do método no parser (ex: parse_order_returns).
        """
        label = action.value

        # ── PARSE ────────────────────────────────────────────────────────
        logger.info("[OBSERVER:%s] Consultando dados...", label)

        parse_log = self._integration_logger.start(
            component_name=f"observer.{label.lower()}",
            process_name=f"ObserverParser.{method_name}",
            message_text=f"Parsing {label}",
        )

        try:
            parser_fn = getattr(self._parser, method_name)
            messages = parser_fn()

            if not messages:
                self._integration_logger.success(
                    parse_log,
                    message_text=f"Nenhum dado para {label}",
                )
                logger.info("[OBSERVER:%s] Nenhum dado encontrado ⏩ Pulando", label)
                return

            self._integration_logger.success(
                parse_log,
                message_text=f"Parsed {len(messages)} mensagem(ns) para {label}",
            )
            logger.info(
                "[OBSERVER:%s] ✔ %d mensagem(ns) parseada(s)",
                label,
                len(messages),
            )
            for msg in messages:
                logger.info(
                    "         → order_code=%s | integration=%s",
                    msg.setup.query_parameters.get("order_code", "?"),
                    msg.integration,
                )

        except Exception as exc:
            self._integration_logger.fail(parse_log, error_details=repr(exc))
            logger.exception("[OBSERVER:%s] ❌ Falha no parse", label)
            return

        # ── PUBLISH ──────────────────────────────────────────────────────
        logger.info("[OBSERVER:%s] Publicando %d mensagem(ns) no PubSub...", label, len(messages))

        publish_log = self._integration_logger.start(
            component_name=f"observer.{label.lower()}.pubsub",
            process_name="ObserverPubSubPublisher.publish",
            message_text=f"Publishing {len(messages)} messages for {label}",
        )

        try:
            message_ids = await self._publisher.publish(
                messages=messages,
                log_uuid=self._log_uuid,
            )

            self._integration_logger.success(
                publish_log,
                message_text=f"Published {len(message_ids)} messages for {label}",
            )
            logger.info(
                "[OBSERVER:%s] ✔ %d mensagem(ns) publicada(s)",
                label,
                len(message_ids),
            )

        except Exception as exc:
            self._integration_logger.fail(publish_log, error_details=repr(exc))
            logger.exception("[OBSERVER:%s] ❌ Falha no publish", label)

