"""
Backup de payloads de VAN no Google Cloud Storage.

Adapta o GCSHandle legado para o padrão atual: cada integração ocupa
um base_path próprio dentro do bucket, com Landing/, Processed/ e Failed/.

Fluxo do pipeline:
  1. upload_landing(filename, content)  → sobe em <base_path>/Landing/<filename>
  2. move_to_processed(filename)         → copia pra Processed/ e apaga origem
  3. move_to_failed(filename)            → copia pra Failed/ e apaga origem

A dependência `google-cloud-storage` é importada de forma lazy: o
módulo carrega mesmo sem ela instalada (necessário pros mocks rodarem
em ambientes de dev/teste).
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)


_LANDING = "Landing"
_PROCESSED = "Processed"
_FAILED = "Failed"


class GCSBackupStorage:
    """
    Implementação real do `VanBackupStorageProtocol` usando GCS.

    Args:
        bucket_name: Nome do bucket (ex: "datahub-merco").
        base_path: Prefixo dentro do bucket (ex: nome da integração).
        service_account_json: Conteúdo JSON da service account (string).
            Quando None, usa as credenciais padrão do ambiente.
    """

    def __init__(
        self,
        bucket_name: str,
        base_path: str,
        service_account_json: Optional[str] = None,
    ) -> None:
        from google.cloud import storage  # type: ignore[import-not-found]

        self._bucket_name = bucket_name
        self._base_path = base_path.rstrip("/") + "/" if base_path else ""

        if service_account_json:
            from google.oauth2 import service_account  # type: ignore[import-not-found]

            credentials_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            self._client = storage.Client(credentials=credentials)
        else:
            self._client = storage.Client()

        self._bucket = self._client.bucket(self._bucket_name)

    def _full_path(self, folder: str, filename: str) -> str:
        return f"{self._base_path}{folder}/{filename}"

    def _to_bytes(self, content: bytes | str) -> bytes:
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    def upload_landing(self, filename: str, content: bytes | str) -> None:
        path = self._full_path(_LANDING, filename)
        blob = self._bucket.blob(path)
        blob.upload_from_file(BytesIO(self._to_bytes(content)), rewind=False)
        logger.info("[GCS] ✔ uploaded gs://%s/%s", self._bucket_name, path)

    def _move(self, filename: str, dest_folder: str) -> None:
        src_path = self._full_path(_LANDING, filename)
        dst_path = self._full_path(dest_folder, filename)

        src_blob = self._bucket.blob(src_path)
        dst_blob = self._bucket.blob(dst_path)

        self._bucket.copy_blob(src_blob, self._bucket, dst_blob.name)
        src_blob.delete()
        logger.info("[GCS] 🔁 %s → %s", src_path, dst_path)

    def move_to_processed(self, filename: str) -> None:
        self._move(filename, _PROCESSED)

    def move_to_failed(self, filename: str) -> None:
        self._move(filename, _FAILED)
