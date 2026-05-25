"""
Envelope-шифрование файлов публичным ключом пользователя.

Формат зашифрованного файла (бинарный):
  key_blob[104] = nonce[24] | ephemeral_pub[32] | nacl_box(aes_key_32)[48]
  aes_nonce[12]
  aes_ciphertext[N+16]   -- N байт файла + 16-байтный GCM-тег

Где key_blob шифруется nacl.box (эфемерная пара отправителя + public_key юзера),
а сам файл шифруется случайным 32-байтным AES-256-GCM ключом.

Браузер расшифровывает через e2ee-client.ts:decryptFile().
"""

import os
import logging
from datetime import datetime

from nacl.public import Box, PrivateKey, PublicKey
import nacl.utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

_NONCE_LEN = 24       # nacl.box nonce
_EPH_PUB_LEN = 32     # ephemeral public key
_AES_KEY_LEN = 32     # AES-256
_AES_NONCE_LEN = 12   # GCM nonce
_BOX_OVERHEAD = 16    # Poly1305 MAC
_KEY_BLOB_LEN = _NONCE_LEN + _EPH_PUB_LEN + _AES_KEY_LEN + _BOX_OVERHEAD  # 104


def encrypt_file_for_user(file_bytes: bytes, public_key_b64: str) -> bytes:
    """Шифрует file_bytes публичным ключом юзера (base64)."""
    import base64
    start_time = datetime.utcnow()

    try:
        pub_bytes = base64.b64decode(public_key_b64)
        recipient_pub = PublicKey(pub_bytes)

        ephemeral_priv = PrivateKey.generate()
        box = Box(ephemeral_priv, recipient_pub)

        aes_key = os.urandom(_AES_KEY_LEN)
        nacl_nonce = nacl.utils.random(_NONCE_LEN)
        # box.encrypt(plaintext, nonce) → EncryptedMessage = nonce + ciphertext
        # .ciphertext содержит только box'd данные (без nonce)
        box_ciphertext = box.encrypt(aes_key, nacl_nonce).ciphertext

        key_blob = nacl_nonce + bytes(ephemeral_priv.public_key) + box_ciphertext

        aes_nonce = os.urandom(_AES_NONCE_LEN)
        aes_ciphertext = AESGCM(aes_key).encrypt(aes_nonce, file_bytes, None)

        encrypted = key_blob + aes_nonce + aes_ciphertext

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(
            "File encrypted successfully",
            extra={
                "action": "encrypt_file",
                "original_size_bytes": len(file_bytes),
                "encrypted_size_bytes": len(encrypted),
                "elapsed_ms": elapsed_ms,
            }
        )

        return encrypted

    except Exception as e:
        logger.error(
            "File encryption failed",
            exc_info=True,
            extra={
                "action": "encrypt_file",
                "error": str(e),
                "original_size_bytes": len(file_bytes),
            }
        )
        raise


def is_encrypted_file(data: bytes) -> bool:
    """Проверяет что data начинается с валидного key_blob (длина >= 116)."""
    return len(data) >= _KEY_BLOB_LEN + _AES_NONCE_LEN


def decrypt_file_for_user(encrypted_bytes: bytes, private_key_b64: str) -> bytes:
    """
    Расшифровывает encrypted_bytes используя private key пользователя.
    NOTE: Обычно это делается в браузере, но может быть полезно для валидации/тестирования.
    """
    import base64
    start_time = datetime.utcnow()

    try:
        if len(encrypted_bytes) < _KEY_BLOB_LEN + _AES_NONCE_LEN:
            raise ValueError(f"Invalid encrypted file: too short ({len(encrypted_bytes)} bytes)")

        # Extract components
        key_blob = encrypted_bytes[:_KEY_BLOB_LEN]
        aes_nonce = encrypted_bytes[_KEY_BLOB_LEN:_KEY_BLOB_LEN + _AES_NONCE_LEN]
        aes_ciphertext = encrypted_bytes[_KEY_BLOB_LEN + _AES_NONCE_LEN:]

        # Decrypt key blob
        priv_bytes = base64.b64decode(private_key_b64)
        recipient_priv = PrivateKey(priv_bytes)

        nacl_nonce = key_blob[:_NONCE_LEN]
        ephemeral_pub = key_blob[_NONCE_LEN:_NONCE_LEN + _EPH_PUB_LEN]
        box_ciphertext = key_blob[_NONCE_LEN + _EPH_PUB_LEN:]

        box = Box(recipient_priv, PublicKey(ephemeral_pub))
        aes_key = box.decrypt(box_ciphertext, nacl_nonce)

        # Decrypt file
        file_bytes = AESGCM(aes_key).decrypt(aes_nonce, aes_ciphertext, None)

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(
            "File decrypted successfully",
            extra={
                "action": "decrypt_file",
                "encrypted_size_bytes": len(encrypted_bytes),
                "decrypted_size_bytes": len(file_bytes),
                "elapsed_ms": elapsed_ms,
            }
        )

        return file_bytes

    except Exception as e:
        logger.error(
            "File decryption failed",
            exc_info=True,
            extra={
                "action": "decrypt_file",
                "error": str(e),
                "encrypted_size_bytes": len(encrypted_bytes),
            }
        )
        raise
