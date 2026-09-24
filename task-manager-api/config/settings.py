"""Configuration read from the environment (playbook RP-01).

The project already declared `python-dotenv` in requirements without using
it; here the dependency finally serves the purpose it was added for.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _flag(nome, padrao="false"):
    return os.getenv(nome, padrao).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-trocar-em-producao")
    DEBUG = _flag("DEBUG")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

    PAGE_SIZE_DEFAULT = int(os.getenv("PAGE_SIZE_DEFAULT", "50"))
    PAGE_SIZE_MAX = int(os.getenv("PAGE_SIZE_MAX", "200"))

    # SMTP credentials moved out of the NotificationService constructor.
    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    VERSAO = "1.0"

    @property
    def cors_origins(self):
        if self.CORS_ORIGINS:
            return self.CORS_ORIGINS
        return "*" if self.DEBUG else []


settings = Settings()
