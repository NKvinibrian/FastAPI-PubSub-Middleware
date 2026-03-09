"""
Módulo de segurança e criptografia da aplicação.

Este módulo fornece utilitários para criptografar e descriptografar
valores sensíveis (como senhas e tokens) usando Fernet (AES-128-CBC),
derivando a chave a partir da SECRET_KEY configurada.

Funções:
    encrypt_value: Criptografa uma string
    decrypt_value: Descriptografa uma string
"""

import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import get_settings


def _get_fernet() -> Fernet:
    """
    Cria uma instância Fernet derivando a chave da SECRET_KEY.

    A SECRET_KEY é convertida em uma chave de 32 bytes via SHA-256 e
    codificada em base64 URL-safe, conforme requerido pelo Fernet.

    Returns:
        Fernet: Instância pronta para criptografar/descriptografar.
    """
    settings = get_settings()
    # Deriva 32 bytes a partir da SECRET_KEY via SHA-256
    key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    """
    Criptografa um valor string usando Fernet (AES-128-CBC + HMAC).

    Args:
        value: Valor em texto plano a ser criptografado.

    Returns:
        str: Valor criptografado e codificado em base64 URL-safe.
    """
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    Descriptografa um valor previamente criptografado com encrypt_value.

    Args:
        encrypted_value: Valor criptografado (base64 URL-safe).

    Returns:
        str: Valor descriptografado em texto plano.

    Raises:
        cryptography.fernet.InvalidToken: Se o token for inválido ou a chave for diferente.
    """
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode())
    return decrypted.decode()
