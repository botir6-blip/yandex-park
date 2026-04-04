from sqlalchemy import select

from app.models import Transaction


def get_driver_transactions(session, driver_id: int, limit: int = 20):
    stmt = (
        select(Transaction)
        .where(Transaction.driver_id == driver_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())
