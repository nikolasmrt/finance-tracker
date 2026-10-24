from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User

ModelT = TypeVar("ModelT")


async def get_owned_or_404(
    session: AsyncSession, model: type[ModelT], object_id: int, user: User, not_found: str
) -> ModelT:
    """Busca um registo do utilizador. 404 tanto para inexistente quanto para de terceiros
    (não revela a existência de dados de outras contas)."""
    instance = await session.scalar(select(model).where(model.id == object_id, model.user_id == user.id))
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, not_found)
    return instance
