import base64
import hashlib

from cryptography.fernet import Fernet


class E2EEService:
    """End-to-End Encryption сервис для работы с ключами и шифрованием"""

    @staticmethod
    def hash_email(email: str) -> str:
        """Генерирует SHA256 хеш email для поиска без расшифровки"""
        return hashlib.sha256(email.encode()).hexdigest()

    @staticmethod
    def encrypt_with_fernet(data: str, key: str) -> str:
        """Шифрует данные Fernet ключом (используется на сервере для backup)"""
        try:
            cipher = Fernet(key.encode() if isinstance(key, str) else key)
            encrypted = cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    @staticmethod
    def decrypt_with_fernet(encrypted_data: str, key: str) -> str:
        """Расшифровывает Fernet данные на сервере"""
        try:
            cipher = Fernet(key.encode() if isinstance(key, str) else key)
            decrypted = cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    @staticmethod
    def encrypt_backup_private_key(private_key_b64: str, password: str) -> str:
        """
        Шифрует backup private key пароль recovery пользователя.

        Flow:
        1. Пользователь вводит recovery password (только в браузере!)
        2. Сервер получает: password + private_key_b64
        3. Сервер генерирует ключ из password: SHA256(password) -> Fernet key
        4. Сервер шифрует: Fernet(private_key_b64, key_from_password)
        5. Результат хранится в БД (зашифрованный!)

        При восстановлении:
        1. Пользователь вводит recovery password
        2. Сервер расшифровывает backup
        3. Браузер расшифровывает (если нужно доп. слой)
        """
        try:
            password_bytes = password.encode()
            password_hash = hashlib.sha256(password_bytes).digest()
            password_key = base64.urlsafe_b64encode(password_hash)

            cipher = Fernet(password_key)
            encrypted_backup = cipher.encrypt(private_key_b64.encode())
            return encrypted_backup.decode()
        except Exception as e:
            raise ValueError(f"Backup encryption failed: {str(e)}")

    @staticmethod
    def decrypt_backup_private_key(encrypted_backup: str, password: str) -> str:
        """Расшифровывает backup private key используя recovery password"""
        try:
            password_bytes = password.encode()
            password_hash = hashlib.sha256(password_bytes).digest()
            password_key = base64.urlsafe_b64encode(password_hash)

            cipher = Fernet(password_key)
            private_key_b64 = cipher.decrypt(encrypted_backup.encode())
            return private_key_b64.decode()
        except Exception as e:
            raise ValueError(f"Backup decryption failed: {str(e)}")
