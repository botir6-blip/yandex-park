from decimal import Decimal, InvalidOperation
import re


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("8") and len(digits) == 9:
        return f"+998{digits}"
    if len(digits) == 9:
        return f"+998{digits}"
    if phone.startswith("+"):
        return phone
    return f"+{digits}" if digits else ""


def mask_card(card_number: str) -> str:
    digits = re.sub(r"\D+", "", card_number or "")
    if len(digits) < 8:
        return digits
    return f"{digits[:6]}****{digits[-4:]}"


def detect_card_type(card_number: str) -> str:
    digits = re.sub(r"\D+", "", card_number or "")
    if digits.startswith("8600") or digits.startswith("9860"):
        return "Uzcard"
    if digits.startswith("9860") or digits.startswith("5614"):
        return "Humo"
    return "Unknown"


def decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
