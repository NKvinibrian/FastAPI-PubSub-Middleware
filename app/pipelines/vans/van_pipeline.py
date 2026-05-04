"""
Pipeline genérica para processamento de pedidos de VANs.

Encapsula o fluxo padrão de qualquer integração de VAN:
    Fetch → Backup (Landing) → Parse → Publish → Backup (Processed/Failed)

O Confirm (marcar pedidos como importados na VAN) acontece no
subscriber do Datasul, APÓS o aceite do pedido.

O que varia entre VANs é:
  - O `fetcher`: implementação específica de cada VAN.
  - O `parser`: mapeamento de campos de cada VAN.
  - O `loop_fn`: função que define as iterações (ex: por industry_code,
    por distributor_code, ou sem loop — retorna [None]).
  - O `backup` (opcional): grava a resposta bruta no GCS pra reprocesso.

Dessa forma, adicionar uma nova VAN significa apenas:
  1. Criar um fetcher específico (ex: IqviaFetcher).
  2. Criar um parser específico (ex: IqviaOrderParser).
  3. Definir um loop_fn (ex: lambda: ["SAN", "RCH"]).
  4. Instanciar VanPipeline e chamar run().
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from app.domain.protocol.vans.backup_storage import VanBackupStorageProtocol
from app.domain.protocol.vans.van_fetcher import VanFetcherProtocol
from app.domain.protocol.vans.order_parser import OrderParserProtocol
from app.domain.services.vans.integration_logger import IntegrationLogger
from app.infrastructure.vans.exceptions.api import EmptyResponse
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher

logger = logging.getLogger(__name__)

_SEPARATOR = "─" * 60


class _StageError(Exception):
    """Sinal interno: alguma etapa falhou — usado pra rotear o backup pra Failed/."""


class VanPipeline:
    """
    Orquestrador genérico do pipeline de VANs.

    Executa o fluxo: Fetch → (Landing) → Parse → Publish → (Processed/Failed)
    para cada contexto retornado pelo `loop_fn`.

    O Confirm (set_orders_as_imported) NÃO faz parte desta pipeline.
    Ele é executado pelo subscriber do Datasul após o aceite do pedido.

    Attributes:
        _fetcher:            Fetcher da VAN (implementa VanFetcherProtocol).
        _parser:             Parser da VAN (implementa OrderParserProtocol).
        _publisher:          Publisher genérico de PubSub.
        _integration_logger: Helper de logging por etapa.
        _loop_fn:            Callable que retorna a lista de contextos de iteração.
                             Retorne [None] para VANs sem loop.
        _log_uuid:           UUID do grupo de processamento.
        _backup:             VanBackupStorageProtocol opcional (GCS, mock, etc.)
        _backup_prefix:      Prefixo do filename gerado em Landing/ (ex: "FF").

    Example::

        pipeline = VanPipeline(
            fetcher=fidelize_fetcher,
            parser=fidelize_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN", "RCH"],
            log_uuid=log_uuid,
            backup=gcs_backup,
            backup_prefix="FF",
        )
        await pipeline.run()
    """

    def __init__(
        self,
        fetcher: VanFetcherProtocol,
        parser: OrderParserProtocol,
        publisher: PrePedidoPubSubPublisher,
        integration_logger: IntegrationLogger,
        loop_fn: Callable[[], list[Any]],
        log_uuid: UUID,
        backup: Optional[VanBackupStorageProtocol] = None,
        backup_prefix: str = "VAN",
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._publisher = publisher
        self._integration_logger = integration_logger
        self._loop_fn = loop_fn
        self._log_uuid = log_uuid
        self._backup = backup
        self._backup_prefix = backup_prefix

    async def run(self) -> None:
        """
        Executa o pipeline para cada contexto retornado pelo loop_fn.

        Itera sobre os contextos (ex: industry_codes) e, para cada um,
        executa fetch → parse → publish.
        """
        contexts = self._loop_fn()

        logger.info(_SEPARATOR)
        logger.info("🚀 VanPipeline STARTED | log_uuid=%s", self._log_uuid)
        logger.info("   Fetcher : %s", type(self._fetcher).__name__)
        logger.info("   Parser  : %s", type(self._parser).__name__)
        logger.info("   Backup  : %s", type(self._backup).__name__ if self._backup else "—")
        logger.info("   Contexts: %s", contexts)
        logger.info(_SEPARATOR)

        for idx, context in enumerate(contexts, 1):
            logger.info("── Context %d/%d: %s ──", idx, len(contexts), context)
            await self._process(context)

        logger.info(_SEPARATOR)
        logger.info("✅ VanPipeline FINISHED | log_uuid=%s", self._log_uuid)
        logger.info(_SEPARATOR)

    def _build_backup_filename(self, label: str) -> str:
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        safe_label = label.replace("/", "_").replace(" ", "_")
        return f"{self._backup_prefix}_{ts}_{safe_label}.json"

    def _safe_upload_landing(self, raw_orders: list[dict], label: str) -> Optional[str]:
        """Sobe pra Landing/. Falha aqui só loga — não derruba o processamento."""
        if self._backup is None:
            return None
        filename = self._build_backup_filename(label)
        try:
            content = json.dumps(raw_orders, ensure_ascii=False, default=str)
            self._backup.upload_landing(filename, content)
            logger.info("[BACKUP] ✔ Landing/%s gravado", filename)
            return filename
        except Exception as exc:
            logger.warning(
                "[BACKUP] ⚠ Falha ao subir Landing/%s context=%s: %s",
                filename, label, exc,
            )
            return None

    def _safe_move(self, filename: Optional[str], success: bool, label: str) -> None:
        """Move pra Processed/ ou Failed/ — falha aqui só loga."""
        if not filename or self._backup is None:
            return
        try:
            if success:
                self._backup.move_to_processed(filename)
                logger.info("[BACKUP] ✔ Processed/%s context=%s", filename, label)
            else:
                self._backup.move_to_failed(filename)
                logger.warning("[BACKUP] ⚠ Failed/%s context=%s", filename, label)
        except Exception as exc:
            logger.warning(
                "[BACKUP] ⚠ Falha ao mover %s (success=%s) context=%s: %s",
                filename, success, label, exc,
            )

    async def _process(self, context: Optional[Any]) -> None:
        """
        Processa um único contexto de iteração.

        Etapas:
            1. Fetch   — busca pedidos brutos na VAN.
            2. Backup Landing — sobe payload bruto no storage.
            3. Parse   — converte para PrePedidoSchema + salva LogPrePedidos.
            4. Publish — publica cada pedido no PubSub (1 por mensagem).
            5. Backup Processed/Failed — move o arquivo conforme o resultado.

        O Confirm acontece no subscriber do Datasul.

        Args:
            context: Parâmetro de iteração (ex: industry_code, ou None).
        """
        label = str(context) if context is not None else "default"

        # ── FETCH ────────────────────────────────────────────────────────────
        raw_orders = await self._stage_fetch(context, label)
        if raw_orders is None:
            return

        # ── BACKUP: Landing ──────────────────────────────────────────────────
        backup_filename = self._safe_upload_landing(raw_orders, label)

        # ── PARSE + PUBLISH (sucesso → Processed, falha → Failed) ────────────
        success = False
        try:
            parsed_orders = self._stage_parse(raw_orders, label)
            await self._stage_publish(parsed_orders, label)
            success = True
        except _StageError:
            # Já logado dentro da etapa — só mantém success=False.
            pass
        finally:
            self._safe_move(backup_filename, success=success, label=label)

    async def _stage_fetch(
        self, context: Optional[Any], label: str
    ) -> Optional[list[dict[str, Any]]]:
        """Fetch isolado. Retorna None se vazio/erro (sem disparar backup)."""
        logger.info("[FETCH] Buscando pedidos... context=%s", label)

        fetch_log = self._integration_logger.start(
            component_name="fetcher",
            process_name=type(self._fetcher).__name__ + ".get_pre_orders",
            message_text=f"Fetching orders [context={label}]",
        )

        try:
            raw_orders = await self._fetcher.get_pre_orders(context=context)

            if not raw_orders:
                self._integration_logger.success(
                    fetch_log,
                    message_text=f"No orders found [context={label}]",
                )
                logger.info("[FETCH] Nenhum pedido encontrado context=%s ⏩ Pulando", label)
                return None

            self._integration_logger.success(
                fetch_log,
                message_text=f"Fetched {len(raw_orders)} orders [context={label}]",
            )
            logger.info("[FETCH] ✔ %d pedido(s) encontrado(s) context=%s", len(raw_orders), label)
            return raw_orders

        except EmptyResponse:
            self._integration_logger.success(
                fetch_log,
                message_text=f"Empty response [context={label}]",
            )
            logger.warning("[FETCH] ⚠ Resposta vazia context=%s", label)
            return None

        except Exception as exc:
            self._integration_logger.fail(fetch_log, error_details=repr(exc))
            logger.exception("[FETCH] ❌ Falha context=%s", label)
            return None

    def _stage_parse(self, raw_orders: list[dict[str, Any]], label: str):
        """Parse — propaga erro como _StageError pra rotear o backup."""
        logger.info("[PARSE] Parseando %d pedido(s)... context=%s", len(raw_orders), label)

        parse_log = self._integration_logger.start(
            component_name="parser",
            process_name=type(self._parser).__name__ + ".parse",
            message_text=f"Parsing {len(raw_orders)} orders [context={label}]",
        )

        try:
            parsed_orders = self._parser.parse(raw_orders)

            self._integration_logger.success(
                parse_log,
                message_text=f"Parsed {len(parsed_orders)} orders [context={label}]",
            )
            logger.info("[PARSE] ✔ %d pedido(s) parseado(s) context=%s", len(parsed_orders), label)
            for order in parsed_orders:
                logger.info(
                    "         → order_code=%s | customer=%s | products=%d",
                    order.order_code,
                    order.customer_code or "?",
                    len(order.products),
                )
            return parsed_orders

        except Exception as exc:
            self._integration_logger.fail(parse_log, error_details=repr(exc))
            logger.exception("[PARSE] ❌ Falha context=%s", label)
            raise _StageError("parse") from exc

    async def _stage_publish(self, parsed_orders, label: str) -> None:
        """Publish — propaga erro como _StageError pra rotear o backup."""
        logger.info(
            "[PUBLISH] Publicando %d pedido(s) no PubSub... context=%s",
            len(parsed_orders), label,
        )

        publish_log = self._integration_logger.start(
            component_name="pubsub",
            process_name="PrePedidoPubSubPublisher.publish",
            message_text=f"Publishing {len(parsed_orders)} orders [context={label}]",
        )

        try:
            message_ids = await self._publisher.publish(
                orders=parsed_orders,
                log_uuid=self._log_uuid,
            )

            self._integration_logger.success(
                publish_log,
                message_text=f"Published {len(message_ids)} messages [context={label}]",
            )
            logger.info(
                "[PUBLISH] ✔ %d mensagem(ns) publicada(s) context=%s",
                len(message_ids), label,
            )
            for mid in message_ids:
                logger.info("          → message_id=%s", mid)

        except Exception as exc:
            self._integration_logger.fail(publish_log, error_details=repr(exc))
            logger.exception("[PUBLISH] ❌ Falha context=%s", label)
            raise _StageError("publish") from exc
