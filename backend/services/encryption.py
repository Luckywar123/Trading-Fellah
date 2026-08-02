"""
Enkripsi password MT5 sebelum disimpan ke Supabase. Pakai Fernet
(symmetric, AES128-CBC + HMAC) — cukup buat "encryption at rest",
key-nya dipegang backend doang (CREDENTIAL_ENCRYPTION_KEY di .env).

PENTING: kalau CREDENTIAL_ENCRYPTION_KEY berubah/hilang, semua password
MT5 yang udah tersimpan gak bisa didekripsi lagi -> user harus re-link
akun MT5 mereka. Backup key ini di tempat aman (secret manager), jangan
cuma di .env server.
"""
from cryptography.fernet import Fernet, InvalidToken
from backend.config import settings


class CredentialCipher:
    def __init__(self, key: str | None = None):
        key = key or settings.CREDENTIAL_ENCRYPTION_KEY
        if not key:
            raise RuntimeError(
                "CREDENTIAL_ENCRYPTION_KEY belum di-set di .env. "
                "Generate dengan: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as e:
            raise ValueError("Gagal dekripsi kredensial — key salah atau data corrupt.") from e


cipher = CredentialCipher() if settings.CREDENTIAL_ENCRYPTION_KEY else None


def get_cipher() -> CredentialCipher:
    global cipher
    if cipher is None:
        cipher = CredentialCipher()
    return cipher
