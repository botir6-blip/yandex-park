import argparse

from sqlalchemy import select

from app.db import db_session
from app.models import Admin
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", default="super_admin")
    args = parser.parse_args()

    with db_session() as session:
        existing = session.execute(select(Admin).where(Admin.login == args.login)).scalar_one_or_none()
        if existing:
            print("Бу логин билан админ аллақачон бор.")
            return

        admin = Admin(
            full_name=args.full_name,
            login=args.login,
            password_hash=hash_password(args.password),
            role=args.role,
            status="active",
        )
        session.add(admin)
        session.flush()
        print(f"Admin яратилди: id={admin.id}, login={admin.login}")


if __name__ == "__main__":
    main()
