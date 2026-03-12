"""
Conector para Bucket (Cloud Storage).

Placeholder para futura implementação de conector com
serviços de armazenamento em nuvem (GCS, S3, Azure Blob, etc.).

Responsabilidade única: transporte de arquivos para/de buckets.
"""

from io import BytesIO
from typing import Optional, Union


class BucketConnector:
    """
    Conector para armazenamento em nuvem (placeholder).

    TODO: Implementar com google-cloud-storage, boto3 ou azure-storage-blob
    conforme o provedor utilizado.
    """

    def __init__(self, bucket_name: str, credentials: Optional[dict] = None) -> None:
        self._bucket_name = bucket_name
        self._credentials = credentials

    def open(self) -> None:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def close(self) -> None:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def list_files(self, path: Optional[str] = None) -> list[str]:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def get_file(self, remote_path: str) -> BytesIO:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def send_file(self, remote_path: str, content: Union[bytes, BytesIO]) -> None:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def delete_file(self, remote_path: str) -> None:
        raise NotImplementedError("BucketConnector not yet implemented.")

    def __enter__(self) -> "BucketConnector":
        self.open()
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        self.close()

