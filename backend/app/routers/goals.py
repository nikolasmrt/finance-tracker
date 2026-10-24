"""Metas financeiras de economia e aportes rápidos."""
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_owner
from app.db.session import get_session
from app.models.models import Goal, User
from app.routers._common import get_owned_or_404
from app.schemas.schemas import GoalCreate, GoalOut, GoalUpdate

router = APIRouter(prefix="/api", tags=["Metas de Economia"])


def _to_goal_out(goal: Goal) -> GoalOut:
    target = float(goal.target_amount)
    current = float(goal.current_amount)
    pct = min(100.0, round((current / target) * 100, 1)) if target > 0 else 0.0
    return GoalOut(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        progress_percentage=pct,
    )


@router.get("/goals/{user_id}", response_model=list[GoalOut])
async def list_goals(
    user_id: int,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc()))
    ).all()
    return [_to_goal_out(g) for g in rows]


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = Goal(
        user_id=user.id,
        title=payload.title,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount or Decimal("0.00"),
        target_date=payload.target_date,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return _to_goal_out(goal)


@router.put("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = await get_owned_or_404(session, Goal, goal_id, user, "Meta não encontrada.")

    if payload.title is not None:
        goal.title = payload.title
    if payload.target_amount is not None:
        goal.target_amount = payload.target_amount
    if payload.current_amount is not None:
        goal.current_amount = payload.current_amount
    elif payload.add_amount is not None:
        goal.current_amount = Decimal(goal.current_amount) + Decimal(payload.add_amount)
    if "target_date" in payload.model_fields_set:
        goal.target_date = payload.target_date

    await session.commit()
    await session.refresh(goal)
    return _to_goal_out(goal)


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = await get_owned_or_404(session, Goal, goal_id, user, "Meta não encontrada.")
    await session.delete(goal)
    await session.commit()
    return {"message": "Meta removida com sucesso!"}
