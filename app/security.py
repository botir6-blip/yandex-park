from cryptography.fernet import Fernet, InvalidToken
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import settings


def _get_fernet() -> Fernet:
    if not settings.card_encryption_key:
        raise RuntimeError("CARD_ENCRYPTION_KEY берилмаган. .env файлини тўлдиринг.")
    return Fernet(settings.card_encryption_key.encode())


def encrypt_card_number(card_number: str) -> str:
    return _get_fernet().encrypt(card_number.encode()).decode()


def decrypt_card_number(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Карта рақамини очиб бўлмади.") from exc


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)
