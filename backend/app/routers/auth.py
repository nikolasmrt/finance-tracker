from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.demo import create_demo_user, purge_expired_demo_users
from app.core.security import (
    burn_password_check,
    clear_auth_cookie,
    get_current_user,
    hash_password,
    limiter,
    set_auth_cookie,
    verify_password,
)
from app.db.session import get_session
from app.models.models import User
from app.schemas.schemas import AuthResponse, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api", tags=["Autenticação"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register_user(
    request: Request,
    payload: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Cria a conta (senha com Bcrypt) e já abre a sessão via cookie HttpOnly."""
    email = payload.email.lower().strip()
    if await session.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está registado no sistema.")

    user = User(name=payload.name, email=email, password_hash=await hash_password(payload.password), is_demo=False)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:  # corrida entre dois registos simultâneos com o mesmo e-mail
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está registado no sistema.")

    set_auth_cookie(response, user)
    return {"message": "Conta criada com sucesso!", "user": user}


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_login)
async def login_user(
    request: Request,
    payload: UserLogin,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Valida as credenciais e grava o JWT em cookie HttpOnly (o token nunca vai no corpo da resposta)."""
    user = await session.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if user is None:
        await burn_password_check(payload.password)
    if user is None or not await verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas. Verifique o e-mail e a senha.")

    set_auth_cookie(response, user)
    return {"message": "Login efetuado com sucesso!", "user": user}


@router.post("/demo", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_demo)
async def start_demo_session(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Modo Convidado 1-click: perfil temporário já preenchido com dados fictícios."""
    await purge_expired_demo_users(session)
    user = await create_demo_user(session)
    await session.commit()

    set_auth_cookie(response, user)
    return {"message": "Sessão de demonstração iniciada!", "user": user}


@router.post("/logout")
async def logout_user(response: Response):
    clear_auth_cookie(response)
    return {"message": "Sessão encerrada com sucesso!"}


@router.get("/me", response_model=UserOut)
async def read_current_user(user: User = Depends(get_current_user)):
    return user
