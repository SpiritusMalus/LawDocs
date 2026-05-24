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

from nacl.public import Box, PrivateKey, PublicKey
import nacl.utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 24       # nacl.box nonce
_EPH_PUB_LEN = 32     # ephemeral public key
_AES_KEY_LEN = 32     # AES-256
_AES_NONCE_LEN = 12   # GCM nonce
_BOX_OVERHEAD = 16    # Poly1305 MAC
_KEY_BLOB_LEN = _NONCE_LEN + _EPH_PUB_LEN + _AES_KEY_LEN + _BOX_OVERHEAD  # 104


def encrypt_file_for_user(file_bytes: bytes, public_key_b64: str) -> bytes:
    """Шифрует file_bytes публичным ключом юзера (base64)."""
    import base64
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

    return key_blob + aes_nonce + aes_ciphertext


def is_encrypted_file(data: bytes) -> bool:
    """Проверяет что data начинается с валидного key_blob (длина >= 116)."""
    return len(data) >= _KEY_BLOB_LEN + _AES_NONCE_LEN
