from decimal import Decimal
from sqlalchemy import select

from app.db import db_session
from app.models import Driver
from app.services.driver_service import ensure_wallet
from app.services.wallet_service import adjust_wallet


def main():
    with db_session() as session:
        phone = "+998901234567"
        driver = session.execute(select(Driver).where(Driver.phone == phone)).scalar_one_or_none()
        if not driver:
            driver = Driver(
                full_name="Тест ҳайдовчи",
                phone=phone,
                language="uz_cyrl",
                status="active",
                park_driver_id="DRV-1001",
            )
            session.add(driver)
            session.flush()
            ensure_wallet(session, driver)
            adjust_wallet(
                session,
                driver,
                main_delta=Decimal("150000"),
                bonus_delta=Decimal("5000"),
                reserve_new=Decimal("20000"),
                transaction_type="balance_topup",
                comment="Demo seed",
                admin_id=None,
            )
            print("Тест ҳайдовчи қўшилди.")
        else:
            print("Тест ҳайдовчи олдиндан бор.")


if __name__ == "__main__":
    main()
