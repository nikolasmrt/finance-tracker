"""
Conexão assíncrona com PostgreSQL otimizada para Serverless (Neon / Supabase).

Decisões de arquitetura:
- `NullPool`: cada função serverless da Vercel é efêmera e pode haver centenas em
  paralelo. Manter um pool local por instância esgotaria as conexões do banco, então
  a conexão é aberta por requisição e devolvida ao pooler externo (PgBouncer do Neon).
- Cache de prepared statements desativado: o PgBouncer em modo *transaction* não
  mantém estado entre transações, e statements preparados nomeados quebrariam.
- Timeouts curtos para que uma função não fique presa aguardando o banco.
"""
import asyncio
import uuid
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_SSL_MODES = {"require", "verify-ca", "verify-full"}


def build_engine_config(raw_url: str) -> tuple[URL, dict]:
    """Converte uma DATABASE_URL padrão (libpq) em URL + connect_args para o asyncpg."""
    url = make_url(raw_url)
    query = dict(url.query)

    # Parâmetros libpq que o asyncpg não entende são traduzidos ou descartados.
    sslmode = str(query.pop("sslmode", query.pop("ssl", ""))).lower()
    query.pop("channel_binding", None)

    connect_args: dict = {
        "timeout": 8,
        "command_timeout": 20,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        "server_settings": {"application_name": "finance_tracker"},
    }
    if sslmode in _SSL_MODES:
        connect_args["ssl"] = sslmode

    return url.set(drivername="postgresql+asyncpg", query=query), connect_args


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    if not settings.database_url:
        raise RuntimeError("A variável de ambiente DATABASE_URL não está configurada.")
    url, connect_args = build_engine_config(settings.database_url)
    return create_async_engine(url, poolclass=NullPool, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)


_schema_ready = False
_schema_lock = asyncio.Lock()


async def ensure_schema() -> None:
    """Garante o DDL uma única vez por instância (a versão do schema evita trabalho repetido)."""
    global _schema_ready
    if _schema_ready:
        return
    async with _schema_lock:
        if _schema_ready:
            return
        from app.models.models import init_db  # import tardio evita dependência circular

        await init_db()
        _schema_ready = True


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependência FastAPI: uma sessão (e uma conexão) por requisição."""
    await ensure_schema()
    async with get_sessionmaker()() as session:
        yield session
