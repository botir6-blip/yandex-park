from sqlalchemy import select

from app.models import Admin
from app.security import verify_password


def authenticate_admin(session, login: str, password: str) -> Admin | None:
    admin = session.execute(select(Admin).where(Admin.login == login)).scalar_one_or_none()
    if not admin:
        return None
    if admin.status != "active":
        return None
    if not verify_password(admin.password_hash, password):
        return None
    return admin


def get_admin(session, admin_id: int) -> Admin | None:
    return session.execute(select(Admin).where(Admin.id == admin_id)).scalar_one_or_none()
