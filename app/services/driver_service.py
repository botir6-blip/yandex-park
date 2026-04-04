from __future__ import annotations

from datetime import datetime
from sqlalchemy import or_, select

from app.models import Driver, DriverWallet
from app.utils import normalize_phone
from app.services.settings_service import get_setting


def get_driver_by_phone(session, phone: str) -> Driver | None:
    normalized = normalize_phone(phone)
    return session.execute(select(Driver).where(Driver.phone == normalized)).scalar_one_or_none()


def get_driver_by_telegram_id(session, telegram_id: int) -> Driver | None:
    return session.execute(select(Driver).where(Driver.telegram_id == telegram_id)).scalar_one_or_none()


def get_driver(session, driver_id: int) -> Driver | None:
    return session.execute(select(Driver).where(Driver.id == driver_id)).scalar_one_or_none()


def bind_driver_to_telegram(session, driver: Driver, telegram_id: int, username: str | None) -> Driver:
    driver.telegram_id = telegram_id
    driver.telegram_username = username
    driver.is_verified = True
    driver.bound_at = datetime.utcnow()
    driver.last_seen_at = datetime.utcnow()
    if not driver.language:
        driver.language = get_setting(session, "default_language", "ru") or "ru"
    if not driver.wallet:
        session.add(DriverWallet(driver_id=driver.id))
    return driver


def touch_driver(session, driver: Driver) -> None:
    driver.last_seen_at = datetime.utcnow()


def search_drivers(session, query: str | None = None):
    stmt = select(Driver).order_by(Driver.id.desc())
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Driver.full_name.ilike(pattern),
                Driver.phone.ilike(pattern),
                Driver.telegram_username.ilike(pattern),
                Driver.park_driver_id.ilike(pattern),
            )
        )
    return list(session.execute(stmt).scalars())


def ensure_wallet(session, driver: Driver) -> DriverWallet:
    if driver.wallet:
        return driver.wallet
    wallet = DriverWallet(driver_id=driver.id)
    session.add(wallet)
    session.flush()
    return wallet
