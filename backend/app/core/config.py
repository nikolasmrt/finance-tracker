"""
Configuração centralizada da aplicação.

Toda variável de ambiente é lida aqui, uma única vez, e exposta como um objeto
imutável (`settings`). Nenhum outro módulo deve chamar `os.getenv` diretamente.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APP_VERSION = "3.0.0"

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent

# O .env local só é usado em desenvolvimento; na Vercel as variáveis já existem no ambiente.
for _env_file in (BACKEND_DIR / ".env", ROOT_DIR / ".env"):
    if _env_file.exists():
        load_dotenv(_env_file)
        break

_DEV_JWT_SECRET = "dev-only-insecure-secret-do-not-use-in-production"

_LOCAL_ORIGINS = (
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _https_origin(host: str) -> str:
    host = host.strip().rstrip("/")
    return host if host.startswith("http") else f"https://{host}"


@dataclass(frozen=True)
class Settings:
    app_version: str
    is_production: bool
    database_url: str | None
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    cookie_name: str
    cookie_secure: bool
    cors_origins: tuple[str, ...]
    cron_secret: str | None
    demo_ttl_hours: int
    rate_limit_enabled: bool
    rate_limit_default: str
    rate_limit_login: str
    rate_limit_register: str
    rate_limit_demo: str
    rate_limit_write: str
    vapid_public_key: str | None
    vapid_private_key: str | None
    vapid_subject: str

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)


def load_settings() -> Settings:
    is_production = os.getenv("VERCEL") == "1" or os.getenv("ENVIRONMENT") == "production"

    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        if is_production:
            raise RuntimeError("JWT_SECRET é obrigatório em produção.")
        jwt_secret = _DEV_JWT_SECRET
    if is_production and len(jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET deve ter ao menos 32 caracteres em produção.")

    # CORS: em produção apenas as origens da própria Vercel (ou FRONTEND_URL);
    # localhost só é aceito fora de produção.
    origins: list[str] = [] if is_production else list(_LOCAL_ORIGINS)
    for var in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        host = os.getenv(var)
        if host:
            origins.append(_https_origin(host))
    origins.extend(_https_origin(o) if "://" not in o else o for o in _env_csv("FRONTEND_URL"))

    return Settings(
        app_version=APP_VERSION,
        is_production=is_production,
        database_url=os.getenv("DATABASE_URL"),
        jwt_secret=jwt_secret,
        jwt_algorithm="HS256",
        access_token_minutes=60 * 24 * 7,
        cookie_name="access_token",
        cookie_secure=is_production,
        cors_origins=tuple(dict.fromkeys(origins)),
        cron_secret=os.getenv("CRON_SECRET") or None,
        demo_ttl_hours=int(os.getenv("DEMO_TTL_HOURS", "4")),
        rate_limit_enabled=_env_bool("RATE_LIMIT_ENABLED", True),
        rate_limit_default=os.getenv("RATE_LIMIT_DEFAULT", "120/minute"),
        rate_limit_login=os.getenv("RATE_LIMIT_LOGIN", "10/minute"),
        rate_limit_register=os.getenv("RATE_LIMIT_REGISTER", "5/minute"),
        rate_limit_demo=os.getenv("RATE_LIMIT_DEMO", "10/minute"),
        rate_limit_write=os.getenv("RATE_LIMIT_WRITE", "60/minute"),
        vapid_public_key=os.getenv("VAPID_PUBLIC_KEY") or None,
        vapid_private_key=os.getenv("VAPID_PRIVATE_KEY") or None,
        vapid_subject=os.getenv("VAPID_SUBJECT", "mailto:admin@example.com"),
    )


settings = load_settings()
