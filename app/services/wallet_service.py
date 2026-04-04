from __future__ import annotations

from decimal import Decimal

from app.models import DriverWallet, Transaction
from app.services.driver_service import ensure_wallet


def available_to_withdraw(wallet: DriverWallet) -> Decimal:
    value = Decimal(wallet.main_balance) - Decimal(wallet.min_reserve_balance)
    return value if value > 0 else Decimal("0")


def adjust_wallet(
    session,
    driver,
    *,
    main_delta: Decimal = Decimal("0"),
    bonus_delta: Decimal = Decimal("0"),
    reserve_new: Decimal | None = None,
    transaction_type: str = "balance_adjustment_plus",
    comment: str | None = None,
    admin_id: int | None = None,
):
    wallet = ensure_wallet(session, driver)

    before_main = Decimal(wallet.main_balance)
    before_bonus = Decimal(wallet.bonus_balance)
    before_reserve = Decimal(wallet.min_reserve_balance)

    after_main = before_main + Decimal(main_delta)
    after_bonus = before_bonus + Decimal(bonus_delta)
    after_reserve = Decimal(reserve_new) if reserve_new is not None else before_reserve

    if after_main < 0 or after_bonus < 0 or after_reserve < 0:
        raise ValueError("Баланс манфий бўлиши мумкин эмас.")

    wallet.main_balance = after_main
    wallet.bonus_balance = after_bonus
    wallet.min_reserve_balance = after_reserve

    tx = Transaction(
        driver_id=driver.id,
        type=transaction_type,
        amount=abs(Decimal(main_delta)) if Decimal(main_delta) != 0 else abs(Decimal(bonus_delta)) if Decimal(bonus_delta) != 0 else abs(after_reserve - before_reserve),
        main_balance_before=before_main,
        main_balance_after=after_main,
        bonus_balance_before=before_bonus,
        bonus_balance_after=after_bonus,
        reserve_balance_before=before_reserve,
        reserve_balance_after=after_reserve,
        comment=comment,
        created_by_admin_id=admin_id,
    )
    session.add(tx)
    session.flush()
    return wallet, tx
