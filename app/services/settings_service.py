from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select

from app.models import Setting


DEFAULT_SETTINGS = {
    "deposit_commission_percent": "1.00",
    "global_min_reserve_balance": "20000.00",
    "min_withdraw_amount": "1000.00",
    "max_withdraw_amount": "10000000.00",
    "support_contact": "@support",
    "default_language": "ru",
}


def get_setting(session, key: str, default: str | None = None) -> str | None:
    row = session.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row:
        return row.value
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(session, key: str, value: str, description: str | None = None) -> None:
    row = session.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row:
        row.value = value
        if description is not None:
            row.description = description
    else:
        session.add(Setting(key=key, value=value, description=description))


def get_decimal_setting(session, key: str, default: str) -> Decimal:
    value = get_setting(session, key, default) or default
    return Decimal(value)
