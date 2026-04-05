from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    card_encryption_key: str = os.getenv("CARD_ENCRYPTION_KEY", "")
    admin_host: str = os.getenv("ADMIN_HOST", "127.0.0.1")
    admin_port: int = int(os.getenv("ADMIN_PORT", "5000"))
    bot_support_contact: str = os.getenv("BOT_SUPPORT_CONTACT", "@support")
    bot_name: str = os.getenv("BOT_NAME", "Prime taxi")
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "ru")


settings = Settings()
