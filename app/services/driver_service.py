from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models import Driver, DriverWallet
from app.services.settings_service import get_setting
from app.utils import normalize_phone


def get_driver_by_phone(session, phone: str) -> Driver | None:
    normalized = normalize_phone(phone)
    stmt = (
        select(Driver)
        .options(
            selectinload(Driver.wallet),
            selectinload(Driver.cards),
            selectinload(Driver.withdrawals),
        )
        .where(Driver.phone == normalized)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_driver_by_telegram_id(session, telegram_id: int) -> Driver | None:
    stmt = (
        select(Driver)
        .options(
            selectinload(Driver.wallet),
            selectinload(Driver.cards),
            selectinload(Driver.withdrawals),
        )
        .where(Driver.telegram_id == telegram_id)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_driver(session, driver_id: int) -> Driver | None:
    stmt = (
        select(Driver)
        .options(
            selectinload(Driver.wallet),
            selectinload(Driver.cards),
            selectinload(Driver.withdrawals),
        )
        .where(Driver.id == driver_id)
    )
    return session.execute(stmt).scalar_one_or_none()


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
    stmt = (
        select(Driver)
        .options(selectinload(Driver.wallet))
        .order_by(Driver.id.desc())
    )
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Driver.full_name.ilike(pattern),
                Driver.phone.ilike(pattern),
                Driver.telegram_username.ilike(pattern),
                Driver.park_driver_id.ilike(pattern),
                Driver.yandex_contractor_profile_id.ilike(pattern),
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


def create_driver(
    session,
    *,
    full_name: str,
    phone: str,
    language: str = "ru",
    status: str = "active",
    park_driver_id: str | None = None,
    yandex_contractor_profile_id: str | None = None,
    note: str | None = None,
):
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        raise ValueError("Телефон рақами нотўғри.")

    full_name = (full_name or "").strip()
    if not full_name:
        raise ValueError("ФИО мажбурий.")

    language = (language or "ru").strip() or "ru"
    if language not in {"ru", "uz_cyrl", "uz_latn"}:
        raise ValueError("Тил нотўғри танланган.")

    status = (status or "active").strip() or "active"
    if status not in {"active", "inactive", "blocked"}:
        raise ValueError("Статус нотўғри танланган.")

    park_driver_id = (park_driver_id or "").strip() or None
    yandex_contractor_profile_id = (yandex_contractor_profile_id or "").strip() or None
    note = (note or "").strip() or None

    if get_driver_by_phone(session, normalized_phone):
        raise ValueError("Бу телефон рақами билан ҳайдовчи аллақачон мавжуд.")

    if park_driver_id:
        existing = session.execute(select(Driver).where(Driver.park_driver_id == park_driver_id)).scalar_one_or_none()
        if existing:
            raise ValueError("Бу ID водителя аллақачон мавжуд.")

    if yandex_contractor_profile_id:
        existing = session.execute(
            select(Driver).where(Driver.yandex_contractor_profile_id == yandex_contractor_profile_id)
        ).scalar_one_or_none()
        if existing:
            raise ValueError("Бу Yandex profile ID аллақачон бошқа ҳайдовчига бириктирилган.")

    driver = Driver(
        full_name=full_name,
        phone=normalized_phone,
        language=language,
        status=status,
        park_driver_id=park_driver_id,
        yandex_contractor_profile_id=yandex_contractor_profile_id,
        note=note,
    )
    session.add(driver)
    session.flush()
    ensure_wallet(session, driver)
    session.flush()
    return driver
