"""
Mock in-memory de `VanBackupStorageProtocol`.

Mantém três dicionários (Landing, Processed, Failed) com o conteúdo
e a ordem de eventos. Permite que os testes assertem o ciclo
completo do backup sem precisar de rede ou GCS de verdade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Folder = Literal["Landing", "Processed", "Failed"]


@dataclass
class MockBackupEvent:
    action: str  # "upload" | "move"
    filename: str
    folder: Folder
    payload: bytes | None = None


@dataclass
class MockBackupStorage:
    """
    Mock in-memory simulando GCS para testes do pipeline.

    Estado público:
      landing/processed/failed: dict filename → bytes do conteúdo.
      events: lista cronológica de operações executadas.
      should_fail_upload: quando True, upload_landing levanta RuntimeError
          (útil pra testar resiliência do pipeline contra falha de backup).
    """

    bucket_name: str = "mock-bucket"
    base_path: str = ""
    landing: dict[str, bytes] = field(default_factory=dict)
    processed: dict[str, bytes] = field(default_factory=dict)
    failed: dict[str, bytes] = field(default_factory=dict)
    events: list[MockBackupEvent] = field(default_factory=list)
    should_fail_upload: bool = False

    def _to_bytes(self, content: bytes | str) -> bytes:
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    def upload_landing(self, filename: str, content: bytes | str) -> None:
        if self.should_fail_upload:
            raise RuntimeError("MockBackupStorage: forced upload failure")
        payload = self._to_bytes(content)
        self.landing[filename] = payload
        self.events.append(
            MockBackupEvent(action="upload", filename=filename, folder="Landing", payload=payload)
        )

    def _pop_from_landing(self, filename: str) -> bytes:
        if filename not in self.landing:
            raise FileNotFoundError(
                f"MockBackupStorage: '{filename}' não encontrado em Landing/"
            )
        return self.landing.pop(filename)

    def move_to_processed(self, filename: str) -> None:
        payload = self._pop_from_landing(filename)
        self.processed[filename] = payload
        self.events.append(
            MockBackupEvent(action="move", filename=filename, folder="Processed", payload=payload)
        )

    def move_to_failed(self, filename: str) -> None:
        payload = self._pop_from_landing(filename)
        self.failed[filename] = payload
        self.events.append(
            MockBackupEvent(action="move", filename=filename, folder="Failed", payload=payload)
        )
