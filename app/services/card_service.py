from __future__ import annotations

import re
from sqlalchemy import select, update

from app.models import DriverCard
from app.security import encrypt_card_number
from app.utils import detect_card_type, mask_card


def validate_card_number(card_number: str) -> str:
    digits = re.sub(r"\D+", "", card_number or "")
    if len(digits) != 16:
        raise ValueError("Карта рақами 16 та рақам бўлиши керак.")
    return digits


def get_active_cards(session, driver_id: int) -> list[DriverCard]:
    stmt = (
        select(DriverCard)
        .where(DriverCard.driver_id == driver_id, DriverCard.status == "active")
        .order_by(DriverCard.is_primary.desc(), DriverCard.id.desc())
    )
    return list(session.execute(stmt).scalars())


def get_card(session, card_id: int, driver_id: int | None = None) -> DriverCard | None:
    stmt = select(DriverCard).where(DriverCard.id == card_id)
    if driver_id is not None:
        stmt = stmt.where(DriverCard.driver_id == driver_id)
    return session.execute(stmt).scalar_one_or_none()


def add_card(session, driver_id: int, card_number: str, holder_name: str | None = None) -> DriverCard:
    digits = validate_card_number(card_number)
    existing_cards = get_active_cards(session, driver_id)
    is_primary = not existing_cards

    if is_primary:
        session.execute(
            update(DriverCard)
            .where(DriverCard.driver_id == driver_id)
            .values(is_primary=False)
        )

    card = DriverCard(
        driver_id=driver_id,
        card_number_encrypted=encrypt_card_number(digits),
        card_mask=mask_card(digits),
        holder_name=holder_name,
        card_type=detect_card_type(digits),
        is_primary=is_primary,
        status="active",
    )
    session.add(card)
    session.flush()
    return card


def set_primary_card(session, driver_id: int, card_id: int) -> DriverCard:
    card = get_card(session, card_id, driver_id)
    if not card or card.status != "active":
        raise ValueError("Карта топилмади ёки фаол эмас.")
    session.execute(
        update(DriverCard)
        .where(DriverCard.driver_id == driver_id)
        .values(is_primary=False)
    )
    card.is_primary = True
    session.flush()
    return card


def delete_card(session, driver_id: int, card_id: int) -> None:
    card = get_card(session, card_id, driver_id)
    if not card:
        raise ValueError("Карта топилмади.")
    card.status = "deleted"
    card.is_primary = False

    active_cards = [c for c in get_active_cards(session, driver_id) if c.id != card_id]
    if active_cards and not any(c.is_primary for c in active_cards):
        active_cards[0].is_primary = True
