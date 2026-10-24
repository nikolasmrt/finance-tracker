import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, status

from database import get_db_cursor

router = APIRouter(prefix="/api/cron", tags=["Manutenção & Cron"])

CRON_SECRET = os.getenv("CRON_SECRET")

def verify_cron_auth(authorization: Optional[str] = Header(None), key: Optional[str] = Query(None)):
    if not CRON_SECRET:
        return  # Em desenvolvimento sem secret configurado, permite a execução
    expected_bearer = f"Bearer {CRON_SECRET}"
    if authorization != expected_bearer and key != CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado. Chave de manutenção/cron inválida."
        )

@router.get("/cleanup-demo", status_code=status.HTTP_200_OK)
@router.post("/cleanup-demo", status_code=status.HTTP_200_OK)
def cleanup_demo_sessions(
    authorization: Optional[str] = Header(None),
    key: Optional[str] = Query(None)
):
    """
    Rotina de limpeza periódica de perfis de teste/demonstração.
    Exclui sessões temporárias com mais de 4 horas de criação,
    limpando em cascata transações, orçamentos e metas associados.
    """
    verify_cron_auth(authorization, key)

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            DELETE FROM users 
            WHERE is_demo = TRUE 
              AND created_at < NOW() - INTERVAL '4 hours';
            """
        )
        deleted_count = cursor.rowcount

    return {
        "status": "success",
        "message": f"Limpeza concluída. {deleted_count} perfis temporários de demonstração foram removidos.",
        "deleted_count": deleted_count
    }
