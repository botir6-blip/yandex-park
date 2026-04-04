from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from app.models import Driver, DriverCard, Transaction, WithdrawalRequest
from app.services.card_service import get_card
from app.services.driver_service import ensure_wallet
from app.services.settings_service import get_decimal_setting
from app.services.wallet_service import available_to_withdraw


def get_open_withdrawal(session, driver_id: int) -> WithdrawalRequest | None:
    stmt = select(WithdrawalRequest).where(
        WithdrawalRequest.driver_id == driver_id,
        WithdrawalRequest.status.in_(["new", "accepted"]),
    )
    return session.execute(stmt).scalar_one_or_none()


def get_withdrawal(session, withdrawal_id: int) -> WithdrawalRequest | None:
    return session.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    ).scalar_one_or_none()


def list_withdrawals(session, status: str | None = None):
    stmt = select(WithdrawalRequest).order_by(WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc())
    if status:
        stmt = stmt.where(WithdrawalRequest.status == status)
    return list(session.execute(stmt).scalars())


def create_withdrawal_request(session, driver: Driver, card_id: int, amount: Decimal, comment: str | None = None) -> WithdrawalRequest:
    wallet = ensure_wallet(session, driver)
    open_req = get_open_withdrawal(session, driver.id)
    if open_req:
        raise ValueError("Сизда ҳали ёпилмаган пул ечиш сўрови бор.")

    min_amount = get_decimal_setting(session, "min_withdraw_amount", "1000.00")
    max_amount = get_decimal_setting(session, "max_withdraw_amount", "10000000.00")

    if amount < min_amount:
        raise ValueError(f"Минимал сумма: {min_amount}")
    if amount > max_amount:
        raise ValueError(f"Максимал сумма: {max_amount}")

    available = available_to_withdraw(wallet)
    if amount > available:
        raise ValueError("Ечиш мумкин бўлган суммадан ортиқ сўров бериш мумкин эмас.")

    card = get_card(session, card_id, driver.id)
    if not card or card.status != "active":
        raise ValueError("Фаол карта топилмади.")

    withdrawal = WithdrawalRequest(
        driver_id=driver.id,
        card_id=card.id,
        requested_amount=amount,
        commission_percent=Decimal("0"),
        commission_amount=Decimal("0"),
        payout_amount=amount,
        status="new",
        driver_comment=comment,
    )
    session.add(withdrawal)
    session.flush()
    return withdrawal


def update_withdrawal_status(session, withdrawal: WithdrawalRequest, new_status: str, admin_id: int | None = None, note: str | None = None) -> WithdrawalRequest:
    if new_status not in {"accepted", "paid", "rejected", "cancelled"}:
        raise ValueError("Нотўғри статус.")

    driver = session.execute(select(Driver).where(Driver.id == withdrawal.driver_id)).scalar_one()
    wallet = ensure_wallet(session, driver)

    if new_status == "accepted":
        if withdrawal.status != "new":
            raise ValueError("Фақат янги сўров қабул қилиниши мумкин.")
        withdrawal.status = "accepted"
        withdrawal.accepted_at = datetime.utcnow()
        withdrawal.processed_by_admin_id = admin_id
        withdrawal.admin_note = note

    elif new_status == "paid":
        if withdrawal.status not in {"new", "accepted"}:
            raise ValueError("Фақат янги ёки қабул қилинган сўров тўланиши мумкин.")
        before_main = Decimal(wallet.main_balance)
        before_bonus = Decimal(wallet.bonus_balance)
        before_reserve = Decimal(wallet.min_reserve_balance)

        if Decimal(withdrawal.requested_amount) > available_to_withdraw(wallet):
            raise ValueError("Балансда етарли маблағ қолмаган.")

        wallet.main_balance = before_main - Decimal(withdrawal.requested_amount)
        withdrawal.status = "paid"
        withdrawal.paid_at = datetime.utcnow()
        withdrawal.processed_by_admin_id = admin_id
        withdrawal.admin_note = note

        session.add(
            Transaction(
                driver_id=driver.id,
                type="withdrawal_paid",
                amount=withdrawal.requested_amount,
                main_balance_before=before_main,
                main_balance_after=wallet.main_balance,
                bonus_balance_before=before_bonus,
                bonus_balance_after=before_bonus,
                reserve_balance_before=before_reserve,
                reserve_balance_after=before_reserve,
                comment=note or "Пул ечиш тўланди",
                related_withdrawal_id=withdrawal.id,
                created_by_admin_id=admin_id,
            )
        )

    elif new_status == "rejected":
        if withdrawal.status not in {"new", "accepted"}:
            raise ValueError("Бу сўровни рад қилиб бўлмайди.")
        withdrawal.status = "rejected"
        withdrawal.rejected_at = datetime.utcnow()
        withdrawal.processed_by_admin_id = admin_id
        withdrawal.admin_note = note

    elif new_status == "cancelled":
        if withdrawal.status not in {"new", "accepted"}:
            raise ValueError("Бу сўровни бекор қилиб бўлмайди.")
        withdrawal.status = "cancelled"
        withdrawal.cancelled_at = datetime.utcnow()
        withdrawal.processed_by_admin_id = admin_id
        withdrawal.admin_note = note

    session.flush()
    return withdrawal
