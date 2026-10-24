from datetime import date

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.finance import budget_status, percentage, resolve_client_today
from app.core.security import get_current_user, limiter, require_owner
from app.db.session import get_session
from app.models.models import Budget, Transaction, User
from app.routers._common import get_owned_or_404
from app.schemas.schemas import BudgetCreate, BudgetOut

router = APIRouter(prefix="/api", tags=["Orçamentos"])


def _month_bounds(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    next_month = (start.replace(day=28) + (date(2000, 1, 5) - date(2000, 1, 1))).replace(day=1)
    return start, next_month


def _to_out(budget: Budget, spent: float) -> BudgetOut:
    limit = float(budget.monthly_limit)
    used = percentage(spent, limit)
    return BudgetOut(
        id=budget.id,
        user_id=budget.user_id,
        category=budget.category,
        monthly_limit=budget.monthly_limit,
        spent_this_month=round(spent, 2),
        percentage_used=used,
        status=budget_status(used),
    )


def _spent_in_month(user_id: int, category, start: date, end: date):
    return (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.category == category,
            Transaction.type == "expense",
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
    )


@router.get("/budgets/{user_id}", response_model=list[BudgetOut])
async def list_budgets(
    today: date | None = None,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    """Tetos mensais por categoria com o gasto do mês corrente e o percentual consumido."""
    start, end = _month_bounds(resolve_client_today(today, date.today()))
    rows = await session.execute(
        select(Budget, func.coalesce(func.sum(Transaction.amount), 0).label("spent"))
        .outerjoin(
            Transaction,
            and_(
                Transaction.user_id == Budget.user_id,
                Transaction.category == Budget.category,
                Transaction.type == "expense",
                Transaction.transaction_date >= start,
                Transaction.transaction_date < end,
            ),
        )
        .where(Budget.user_id == user.id)
        .group_by(Budget.id)
        .order_by(Budget.category)
    )
    return [_to_out(budget, float(spent)) for budget, spent in rows.all()]


@router.post("/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_write)
async def upsert_budget(
    request: Request,
    payload: BudgetCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cria ou atualiza o teto mensal da categoria (um por categoria)."""
    budget = await session.scalar(
        pg_insert(Budget)
        .values(user_id=user.id, category=payload.category, monthly_limit=payload.monthly_limit)
        .on_conflict_do_update(constraint="uq_user_category", set_={"monthly_limit": payload.monthly_limit})
        .returning(Budget)
    )
    start, end = _month_bounds(date.today())
    spent = await session.scalar(_spent_in_month(user.id, budget.category, start, end))
    await session.commit()
    return _to_out(budget, float(spent))


@router.delete("/budgets/{budget_id}")
@limiter.limit(settings.rate_limit_write)
async def delete_budget(
    request: Request,
    budget_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    budget = await get_owned_or_404(session, Budget, budget_id, user, "Orçamento não encontrado.")
    await session.delete(budget)
    await session.commit()
    return {"message": "Orçamento removido com sucesso!"}
