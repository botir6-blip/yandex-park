from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from app.config import settings

if not settings.database_url:
    raise RuntimeError("DATABASE_URL бўш. .env файлини тўлдиринг.")

db_url = settings.database_url.strip()

if db_url.startswith("postgresql+psycopg2://"):
    db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url, future=True, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)
)
db_session = SessionLocal
Base = declarative_base()


def ensure_runtime_schema() -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE IF EXISTS drivers ADD COLUMN IF NOT EXISTS yandex_contractor_profile_id VARCHAR(100)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_drivers_yandex_contractor_profile_id ON drivers(yandex_contractor_profile_id) WHERE yandex_contractor_profile_id IS NOT NULL"))
    except Exception:
        # Жонли муҳитда база ҳали яратилмаган бўлиши мумкин; schema.sql кейин қўйилади.
        pass


ensure_runtime_schema()
