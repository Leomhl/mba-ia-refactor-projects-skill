"""Application configuration, read from the environment (playbook RP-01)."""
import os


def _flag(nome, padrao="false"):
    return os.getenv(nome, padrao).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-trocar-em-producao")
    DEBUG = _flag("DEBUG")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DB_PATH = os.getenv("DB_PATH", "loja.db")

    # Token required by the administrative routes. With no value set, they
    # stay unavailable — the safe default is to deny.
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

    # Origins allowed by CORS. "*" is only accepted in development mode.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

    # Pagination cap for list endpoints.
    PAGE_SIZE_DEFAULT = int(os.getenv("PAGE_SIZE_DEFAULT", "50"))
    PAGE_SIZE_MAX = int(os.getenv("PAGE_SIZE_MAX", "200"))

    VERSAO = "1.0.0"

    @property
    def cors_origins(self):
        if self.CORS_ORIGINS:
            return self.CORS_ORIGINS
        return "*" if self.DEBUG else []


settings = Settings()
