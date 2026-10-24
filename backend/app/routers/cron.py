"""Rotina agendada (Vercel Cron) para expurgo automático de sessões de demonstração expiradas."""
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.demo import purge_expired_demo_users
from app.db.session import get_session

router = APIRouter(prefix="/api/cron", tags=["Manutenção & Cron"])


def verify_cron_auth(
    authorization: str | None = Header(default=None),
    key: str | None = Query(default=None),
) -> None:
    if not settings.cron_secret:
        return  # Em desenvolvimento local sem CRON_SECRET configurado
    expected_bearer = f"Bearer {settings.cron_secret}"
    valid_header = authorization is not None and hmac.compare_digest(authorization, expected_bearer)
    valid_query = key is not None and hmac.compare_digest(key, settings.cron_secret)
    if not (valid_header or valid_query):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado. Chave de manutenção/cron inválida.",
        )


@router.get("/cleanup-demo")
@router.post("/cleanup-demo")
async def cleanup_demo_sessions(
    authorization: str | None = Header(default=None),
    key: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Remove perfis temporários de demonstração (is_demo = TRUE) expirados."""
    verify_cron_auth(authorization, key)
    deleted_count = await purge_expired_demo_users(session)
    await session.commit()
    return {
        "status": "success",
        "message": f"Limpeza concluída. {deleted_count} perfis temporários de demonstração foram removidos.",
        "deleted_count": deleted_count,
    }
