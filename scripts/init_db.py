from pathlib import Path
import psycopg
from app.config import settings


def to_psycopg_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def main():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL берилмаган.")
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    dsn = to_psycopg_dsn(settings.database_url)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Schema муваффақиятли қўйилди.")


if __name__ == "__main__":
    main()
