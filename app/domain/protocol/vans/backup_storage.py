"""
Protocolo de backup de respostas brutas das VANs.

Mesmo padrão do legado (GCSHandle): cada integração tem um diretório
base com três pastas — Landing/, Processed/, Failed/. O pipeline sobe
o payload bruto em Landing/ logo após o fetch e, ao final do
processamento, move para Processed/ (sucesso) ou Failed/ (erro).
"""

from typing import Protocol


class VanBackupStorageProtocol(Protocol):
    """
    Backup de respostas das VANs em armazenamento de objeto.

    Implementações:
      - GCSBackupStorage: real, sobe pra um bucket no GCS.
      - MockBackupStorage: in-memory pros testes.
    """

    def upload_landing(self, filename: str, content: bytes | str) -> None:
        """
        Sobe o payload bruto para a pasta Landing/ do bucket.

        Raises:
            Exception: erro de transporte/permissão (deve ser tratado
                pelo chamador para decidir se é fatal).
        """
        ...

    def move_to_processed(self, filename: str) -> None:
        """Move o arquivo de Landing/ para Processed/."""
        ...

    def move_to_failed(self, filename: str) -> None:
        """Move o arquivo de Landing/ para Failed/ (para reprocesso manual)."""
        ...
