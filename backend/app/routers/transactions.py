import csv
import io
import math
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.finance import build_forecast, build_timeline, classify_bill, resolve_client_today
from app.core.sanitize import clean_text, escape_like, normalize_tag
from app.core.security import get_current_user, limiter, require_owner
from app.db.session import get_session
from app.models.models import Transaction, User
from app.routers._common import get_owned_or_404
from app.schemas.schemas import (
    BillItem,
    BillsResponse,
    CategoryBreakdown,
    PaginatedTransactions,
    SmartForecast,
    TagUsage,
    TimelineResponse,
    TransactionCreate,
    TransactionEnvelope,
    TransactionOut,
    TransactionsSummary,
    TransactionType,
    TransactionUpdate,
)

router = APIRouter(prefix="/api", tags=["Transações"])

_INCOME_AMOUNT = case((Transaction.type == "income", Transaction.amount), else_=0)
_EXPENSE_AMOUNT = case((Transaction.type == "expense", Transaction.amount), else_=0)
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _f(value: Decimal | int | None) -> float:
    return float(value or 0)


def _settled_until(user_id: int, today: date) -> list:
    """Movimentações que já afetam o saldo: liquidadas e com data até hoje."""
    return [
        Transaction.user_id == user_id,
        Transaction.is_paid.is_(True),
        Transaction.transaction_date <= today,
    ]


async def _get_owned_transaction(session: AsyncSession, transaction_id: int, user: User) -> Transaction:
    return await get_owned_or_404(session, Transaction, transaction_id, user, "Transação não encontrada.")


# --- CRUD -----------------------------------------------------------------------------


@router.post("/transactions", response_model=TransactionEnvelope, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_write)
async def create_transaction(
    request: Request,
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = Transaction(
        user_id=user.id,
        type=payload.type,
        amount=payload.amount,
        description=payload.description,
        category=payload.category,
        transaction_date=payload.transaction_date or date.today(),
        tags=payload.tags,
        due_date=payload.due_date,
        is_paid=payload.is_paid,
    )
    session.add(tx)
    await session.commit()
    return {"message": "Transação criada com sucesso!", "transaction": tx}


@router.put("/transactions/{transaction_id}", response_model=TransactionEnvelope)
@limiter.limit(settings.rate_limit_write)
async def update_transaction(
    request: Request,
    transaction_id: int,
    payload: TransactionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await _get_owned_transaction(session, transaction_id, user)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo fornecido para atualização.")
    for field, value in changes.items():
        setattr(tx, field, value)
    await session.commit()
    return {"message": "Transação atualizada com sucesso!", "transaction": tx}


@router.patch("/transactions/{transaction_id}/toggle-paid")
@limiter.limit(settings.rate_limit_write)
async def toggle_transaction_paid(
    request: Request,
    transaction_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await _get_owned_transaction(session, transaction_id, user)
    tx.is_paid = not tx.is_paid
    await session.commit()
    return {"message": "Conta liquidada." if tx.is_paid else "Conta marcada como pendente.", "is_paid": tx.is_paid}


@router.delete("/transactions/{transaction_id}")
@limiter.limit(settings.rate_limit_write)
async def delete_transaction(
    request: Request,
    transaction_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await _get_owned_transaction(session, transaction_id, user)
    await session.delete(tx)
    await session.commit()
    return {"message": "Transação removida com sucesso!"}


# --- Listagem com paginação e filtros -------------------------------------------------


@router.get("/transactions/{user_id}", response_model=PaginatedTransactions)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    tx_type: TransactionType | None = Query(None, alias="type"),
    category: str | None = Query(None, max_length=50),
    search: str | None = Query(None, max_length=100),
    tag: str | None = Query(None, max_length=40),
    is_paid: bool | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    conditions = [Transaction.user_id == user.id]
    if tx_type:
        conditions.append(Transaction.type == tx_type)
    if category:
        conditions.append(Transaction.category == category)
    if search and (term := escape_like(clean_text(search))):
        conditions.append(Transaction.description.ilike(f"%{term}%", escape="\\"))
    if tag and (normalized := normalize_tag(tag)):
        conditions.append(Transaction.tags.contains([normalized]))
    if is_paid is not None:
        conditions.append(Transaction.is_paid.is_(is_paid))
    if start_date:
        conditions.append(Transaction.transaction_date >= start_date)
    if end_date:
        conditions.append(Transaction.transaction_date <= end_date)

    total_records = await session.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0
    items = (
        await session.scalars(
            select(Transaction)
            .where(*conditions)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset((page - 1) * limit)
        )
    ).all()

    return {
        "transactions": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": max(1, math.ceil(total_records / limit)),
            "current_page": page,
        },
    }


@router.get("/transactions/{user_id}/tags", response_model=list[TagUsage])
async def list_tags(user: User = Depends(require_owner), session: AsyncSession = Depends(get_session)):
    """Etiquetas em uso (mais frequentes primeiro) para os filtros do histórico."""
    unnested = select(func.unnest(Transaction.tags).label("tag")).where(Transaction.user_id == user.id).subquery()
    rows = await session.execute(
        select(unnested.c.tag, func.count().label("uses"))
        .group_by(unnested.c.tag)
        .order_by(desc("uses"), unnested.c.tag)
        .limit(50)
    )
    return [{"tag": tag, "uses": uses} for tag, uses in rows.all()]


# --- Resumo, linha do tempo e contas (agregações feitas no PostgreSQL) -----------------


@router.get("/transactions/{user_id}/summary", response_model=TransactionsSummary)
async def get_summary(
    today: date | None = None,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    """Totais, categorias e previsão. Contas pendentes não alteram o saldo; entram em `pending_*`."""
    effective_today = resolve_client_today(today, date.today())
    settled = _settled_until(user.id, effective_today)

    category_rows = (
        await session.execute(
            select(
                Transaction.category,
                func.coalesce(func.sum(_INCOME_AMOUNT), 0).label("income"),
                func.coalesce(func.sum(_EXPENSE_AMOUNT), 0).label("expense"),
                func.count().label("total_n"),
                func.count().filter(Transaction.type == "income").label("income_n"),
                func.count().filter(Transaction.type == "expense").label("expense_n"),
            )
            .where(*settled)
            .group_by(Transaction.category)
            .order_by(desc(func.sum(Transaction.amount)))
        )
    ).all()

    first_date, last_date = (
        await session.execute(select(func.min(Transaction.transaction_date), func.max(Transaction.transaction_date)).where(*settled))
    ).one()

    pending_income, pending_expense, pending_count = (
        await session.execute(
            select(
                func.coalesce(func.sum(_INCOME_AMOUNT), 0),
                func.coalesce(func.sum(_EXPENSE_AMOUNT), 0),
                func.count(),
            ).where(Transaction.user_id == user.id, Transaction.is_paid.is_(False))
        )
    ).one()

    total_income = sum(_f(r.income) for r in category_rows)
    total_expense = sum(_f(r.expense) for r in category_rows)
    count = sum(r.total_n for r in category_rows)

    return {
        "total_deposits": round(total_income, 2),
        "total_expenses": round(total_expense, 2),
        "net_balance": round(total_income - total_expense, 2),
        "transactions_count": count,
        "income_count": sum(r.income_n for r in category_rows),
        "expense_count": sum(r.expense_n for r in category_rows),
        "pending_income": round(_f(pending_income), 2),
        "pending_expenses": round(_f(pending_expense), 2),
        "pending_count": pending_count,
        "categories": [
            CategoryBreakdown(
                category=r.category,
                total_income=round(_f(r.income), 2),
                total_expense=round(_f(r.expense), 2),
                net=round(_f(r.income) - _f(r.expense), 2),
                count=r.total_n,
            )
            for r in category_rows
        ],
        "forecast": SmartForecast(**build_forecast(total_income, total_expense, first_date, last_date, count)),
    }


@router.get("/transactions/{user_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    days: int = Query(30, ge=7, le=365),
    today: date | None = None,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    """Evolução patrimonial: saldo acumulado dia a dia na janela pedida."""
    end = resolve_client_today(today, date.today())
    start = end - timedelta(days=days - 1)
    settled = _settled_until(user.id, end)
    signed_amount = case((Transaction.type == "income", Transaction.amount), else_=-Transaction.amount)

    opening = await session.scalar(
        select(func.coalesce(func.sum(signed_amount), 0)).where(*settled, Transaction.transaction_date < start)
    )
    rows = (
        await session.execute(
            select(
                Transaction.transaction_date,
                func.coalesce(func.sum(_INCOME_AMOUNT), 0),
                func.coalesce(func.sum(_EXPENSE_AMOUNT), 0),
            )
            .where(*settled, Transaction.transaction_date >= start)
            .group_by(Transaction.transaction_date)
        )
    ).all()

    points = build_timeline(_f(opening), {d: (_f(i), _f(e)) for d, i, e in rows}, start, end)
    return {
        "days": days,
        "points": points,
        "starting_balance": round(_f(opening), 2),
        "ending_balance": points[-1]["cumulative_balance"],
        "total_days": len(points),
    }


@router.get("/transactions/{user_id}/bills", response_model=BillsResponse)
async def get_bills(
    today: date | None = None,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    """Contas com vencimento: pendentes (todas) e liquidadas nos últimos 30 dias."""
    effective_today = resolve_client_today(today, date.today())
    rows = (
        await session.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.due_date.is_not(None),
                or_(Transaction.is_paid.is_(False), Transaction.due_date >= effective_today - timedelta(days=30)),
            )
            .order_by(Transaction.due_date.asc(), Transaction.id.asc())
            .limit(200)
        )
    ).all()

    bills: list[BillItem] = []
    counts = {"overdue": 0, "today": 0, "upcoming": 0}
    pending_total = 0.0
    for tx in rows:
        status_name, days_diff, label = classify_bill(tx.due_date, tx.is_paid, effective_today)
        if status_name != "paid":
            counts[status_name] += 1
            pending_total += _f(tx.amount)
        bills.append(
            BillItem(
                id=tx.id,
                type=tx.type,
                amount=_f(tx.amount),
                description=tx.description,
                category=tx.category,
                due_date=tx.due_date,
                is_paid=tx.is_paid,
                tags=tx.tags or [],
                status=status_name,
                days_diff=days_diff,
                label=label,
            )
        )

    return BillsResponse(
        bills=bills,
        overdue_count=counts["overdue"],
        today_count=counts["today"],
        upcoming_count=counts["upcoming"],
        total_pending_amount=round(pending_total, 2),
    )


# --- Exportação -----------------------------------------------------------------------


def _csv_safe(value) -> str:
    """Neutraliza injeção de fórmulas em planilhas (Excel/Sheets) em campos de texto livres."""
    text_value = "" if value is None else str(value)
    return f"'{text_value}" if text_value.startswith(_CSV_FORMULA_PREFIXES) else text_value


@router.get("/transactions/{user_id}/export")
async def export_transactions(
    format: str = Query("csv", pattern="^(csv|json)$"),
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        )
    ).all()

    if format == "json":
        return {"transactions": [TransactionOut.model_validate(tx).model_dump(mode="json") for tx in rows]}

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Tipo", "Valor", "Descricao", "Categoria", "Data", "Tags", "Vencimento", "Liquidado"])
    for tx in rows:
        writer.writerow(
            [
                tx.id,
                "Receita" if tx.type == "income" else "Despesa",
                f"{tx.amount:.2f}".replace(".", ","),
                _csv_safe(tx.description),
                _csv_safe(tx.category),
                tx.transaction_date.isoformat(),
                _csv_safe(" ".join(f"#{t}" for t in tx.tags or [])),
                tx.due_date.isoformat() if tx.due_date else "",
                "Sim" if tx.is_paid else "Nao",
            ]
        )
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=finance_tracker_{user.id}.csv"},
    )
