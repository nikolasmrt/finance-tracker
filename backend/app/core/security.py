"""
Segurança da aplicação: Bcrypt, JWT em cookie HttpOnly, rate limiting e dependências de autenticação.

O token JWT trafega exclusivamente em cookie `HttpOnly; SameSite=Lax` (e `Secure` em produção),
portanto nunca fica acessível a JavaScript e não pode ser roubado via XSS.
"""
import functools
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from passlib.context import CryptContext
from slowapi import Limiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models.models import User

# --- Rate limiting --------------------------------------------------------------------


def client_ip(request: Request) -> str:
    """IP real do cliente atrás da CDN/proxy da Vercel (que sobrescreve esses cabeçalhos)."""
    for header in ("x-vercel-forwarded-for", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# Armazenamento em memória: o limite vale por instância serverless (proteção de melhor esforço).
limiter = Limiter(
    key_func=client_ip,
    default_limits=[settings.rate_limit_default],
    enabled=settings.rate_limit_enabled,
)

# --- Senhas ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    """Bcrypt é CPU-bound: roda em thread para não bloquear o event loop."""
    return await run_in_threadpool(_pwd_context.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await run_in_threadpool(_pwd_context.verify, password, password_hash)


@functools.cache
def _dummy_hash() -> str:
    return _pwd_context.hash(secrets.token_urlsafe(16))


async def burn_password_check(password: str) -> None:
    """Gasta o mesmo tempo de uma verificação real quando o e-mail não existe (evita enumeração)."""
    await verify_password(password, _dummy_hash())


# --- JWT e cookie ---------------------------------------------------------------------


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "is_demo": bool(user.is_demo),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=create_access_token(user),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


# --- Dependências de autenticação -----------------------------------------------------


async def get_optional_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User | None:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not str(payload.get("sub", "")).isdigit():
        return None
    return await session.scalar(select(User).where(User.id == int(payload["sub"])))


async def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não autenticada ou expirada. Faça login para continuar.",
        )
    return user


async def require_owner(user_id: int, user: User = Depends(get_current_user)) -> User:
    """Para rotas `/{user_id}/...`: o recurso solicitado precisa pertencer ao utilizador autenticado."""
    if user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a dados de outro utilizador.")
    return user
