import math
import io
import csv
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse

from database import get_db_cursor
from schemas import (
    TransactionCreate, 
    TransactionUpdate, 
    TransactionResponse,
    TransactionsSummary,
    CategoryBreakdownItem,
    SmartForecast,
    PaginatedTransactionsResponse,
    PaginationMeta,
    TimelineResponse,
    TimelinePoint,
    BillItem,
    BillsResponse
)
from routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Transações"])

@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(
    tx: TransactionCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Cria uma nova movimentação financeira (receita ou despesa) com suporte a tags,
    data de vencimento e status de liquidação.
    """
    effective_user_id = current_user["id"] if current_user else tx.user_id
    tx_date = tx.transaction_date or date.today()
    tags = (tx.tags or "").strip()
    due_date = tx.due_date
    is_paid = tx.is_paid if tx.is_paid is not None else True

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO transactions (user_id, type, amount, description, category, transaction_date, tags, due_date, is_paid)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, type, amount, description, category, transaction_date, tags, due_date, is_paid;
            """,
            (effective_user_id, tx.type, tx.amount, tx.description.strip(), tx.category.strip(), tx_date, tags, due_date, is_paid)
        )
        new_tx = cursor.fetchone()
        return {"message": "Transação criada com sucesso!", "transaction": new_tx}

@router.get("/transactions/{user_id}", response_model=PaginatedTransactionsResponse, status_code=status.HTTP_200_OK)
def get_transactions(
    user_id: int,
    page: int = Query(1, ge=1, description="Número da página atual"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    type: Optional[str] = Query(None, description="Filtrar por tipo: 'income' ou 'expense'"),
    category: Optional[str] = Query(None, description="Filtrar por categoria específica"),
    search: Optional[str] = Query(None, description="Busca textual na descrição"),
    tag: Optional[str] = Query(None, description="Filtrar por tag/hashtag específica"),
    is_paid: Optional[bool] = Query(None, description="Filtrar por status de liquidação"),
    start_date: Optional[date] = Query(None, description="Data inicial do filtro"),
    end_date: Optional[date] = Query(None, description="Data final do filtro"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Lista movimentações financeiras com suporte a paginação serverless,
    filtros avançados (categoria, tipo, tag, status de liquidação) e busca textual.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    base_where = "WHERE user_id = %s"
    params = [effective_user_id]

    if type in ("income", "expense"):
        base_where += " AND type = %s"
        params.append(type)

    if category:
        base_where += " AND category = %s"
        params.append(category)

    if search:
        base_where += " AND description ILIKE %s"
        params.append(f"%{search.strip()}%")

    if tag:
        base_where += " AND tags ILIKE %s"
        params.append(f"%{tag.strip()}%")

    if is_paid is not None:
        base_where += " AND is_paid = %s"
        params.append(is_paid)

    if start_date:
        base_where += " AND transaction_date >= %s"
        params.append(start_date)

    if end_date:
        base_where += " AND transaction_date <= %s"
        params.append(end_date)

    count_query = f"SELECT COUNT(*) as total FROM transactions {base_where};"

    offset = (page - 1) * limit
    data_query = f"""
        SELECT id, user_id, type, amount, description, category, transaction_date, tags, due_date, is_paid 
        FROM transactions 
        {base_where}
        ORDER BY transaction_date DESC, id DESC
        LIMIT %s OFFSET %s;
    """

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(count_query, tuple(params))
        total_records = cursor.fetchone()["total"]

        cursor.execute(data_query, tuple(params + [limit, offset]))
        transactions = cursor.fetchall()

    total_pages = max(1, math.ceil(total_records / limit))

    return {
        "transactions": transactions,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.get("/transactions/{user_id}/summary", response_model=TransactionsSummary)
def get_transactions_summary(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retorna o resumo consolidado do utilizador com cálculos de agregações (SUM, COUNT)
    otimizados diretamente no PostgreSQL, além da Previsão Inteligente 30d.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    with get_db_cursor(commit=False) as cursor:
        # 1. Totais de receitas e despesas agregados no banco
        cursor.execute(
            """
            SELECT 
                type, 
                COALESCE(SUM(amount), 0) AS total, 
                COUNT(*) AS count 
            FROM transactions 
            WHERE user_id = %s 
            GROUP BY type;
            """,
            (effective_user_id,)
        )
        type_totals = {row["type"]: float(row["total"]) for row in cursor.fetchall()}
        total_income = type_totals.get("income", 0.0)
        total_expense = type_totals.get("expense", 0.0)
        net_balance = round(total_income - total_expense, 2)

        # 2. Agrupamento por categoria diretamente via SQL
        cursor.execute(
            """
            SELECT 
                category,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense,
                COUNT(*) AS count
            FROM transactions 
            WHERE user_id = %s 
            GROUP BY category
            ORDER BY (COALESCE(SUM(amount), 0)) DESC;
            """,
            (effective_user_id,)
        )
        cat_rows = cursor.fetchall()

        # 3. Intervalo de datas para a Previsão Inteligente
        cursor.execute(
            """
            SELECT 
                MIN(transaction_date) as first_date, 
                MAX(transaction_date) as last_date, 
                COUNT(*) as total_count
            FROM transactions 
            WHERE user_id = %s;
            """,
            (effective_user_id,)
        )
        date_stats = cursor.fetchone()

    categories_list = []
    for row in cat_rows:
        inc = float(row["total_income"])
        exp = float(row["total_expense"])
        categories_list.append(CategoryBreakdownItem(
            category=row["category"],
            total_income=round(inc, 2),
            total_expense=round(exp, 2),
            net=round(inc - exp, 2),
            count=int(row["count"])
        ))

    total_transactions_count = int(date_stats["total_count"]) if date_stats else 0
    first_date = date_stats["first_date"] if date_stats else None
    last_date = date_stats["last_date"] if date_stats else None

    # Cálculo da Previsão Inteligente para 30 dias
    days_span = 30
    if first_date and last_date:
        diff_days = max(1, (last_date - first_date).days)
        days_span = min(max(diff_days, 7), 90)

    daily_avg_expense = total_expense / days_span if total_expense > 0 else 0.0
    daily_avg_income = total_income / days_span if total_income > 0 else 0.0

    projected_expense_30d = round(daily_avg_expense * 30, 2)
    projected_income_30d = round(daily_avg_income * 30, 2)
    projected_balance_30d = round(net_balance + projected_income_30d - projected_expense_30d, 2)

    savings_rate = round(((total_income - total_expense) / total_income) * 100, 1) if total_income > 0 else 0.0

    if total_transactions_count == 0:
        status_forecast = "neutral"
        forecast_msg = "Adicione as suas primeiras movimentações para gerar projeções analíticas."
    elif projected_balance_30d >= net_balance and net_balance >= 0:
        status_forecast = "positive"
        forecast_msg = f"Tendência financeira favorável! Previsão de poupança com taxa estimada de {max(0, savings_rate)}%."
    elif projected_balance_30d < 0:
        status_forecast = "critical"
        forecast_msg = f"Atenção: no ritmo atual de gastos (R$ {round(daily_avg_expense, 2):.2f}/dia), seu saldo pode ficar negativo."
    else:
        status_forecast = "warning"
        forecast_msg = "Ritmo de gastos moderado. Controle despesas para manter o saldo positivo nos próximos 30 dias."

    forecast = SmartForecast(
        daily_average_expense=round(daily_avg_expense, 2),
        daily_average_income=round(daily_avg_income, 2),
        projected_expense_30d=projected_expense_30d,
        projected_income_30d=projected_income_30d,
        projected_balance_30d=projected_balance_30d,
        savings_rate=savings_rate,
        status=status_forecast,
        message=forecast_msg
    )

    return TransactionsSummary(
        total_deposits=round(total_income, 2),
        total_expenses=round(total_expense, 2),
        net_balance=net_balance,
        transactions_count=total_transactions_count,
        categories=categories_list,
        forecast=forecast
    )

@router.put("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
def update_transaction(
    transaction_id: int,
    tx_update: TransactionUpdate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Atualiza campos de uma transação existente com verificação de propriedade.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id FROM transactions WHERE id = %s;", (transaction_id,))
        existing_tx = cursor.fetchone()

        if not existing_tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transação não encontrada."
            )

        if current_user and existing_tx["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta transação."
            )

        fields = []
        params = []

        if tx_update.type is not None:
            fields.append("type = %s")
            params.append(tx_update.type)

        if tx_update.amount is not None:
            fields.append("amount = %s")
            params.append(tx_update.amount)

        if tx_update.description is not None:
            fields.append("description = %s")
            params.append(tx_update.description.strip())

        if tx_update.category is not None:
            fields.append("category = %s")
            params.append(tx_update.category.strip())

        if tx_update.transaction_date is not None:
            fields.append("transaction_date = %s")
            params.append(tx_update.transaction_date)

        if tx_update.tags is not None:
            fields.append("tags = %s")
            params.append(tx_update.tags.strip())

        if tx_update.due_date is not None:
            fields.append("due_date = %s")
            params.append(tx_update.due_date)

        if tx_update.is_paid is not None:
            fields.append("is_paid = %s")
            params.append(tx_update.is_paid)

        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo fornecido para atualização."
            )

        params.append(transaction_id)
        update_query = f"""
            UPDATE transactions 
            SET {', '.join(fields)} 
            WHERE id = %s 
            RETURNING id, user_id, type, amount, description, category, transaction_date, tags, due_date, is_paid;
        """
        cursor.execute(update_query, tuple(params))
        updated_tx = cursor.fetchone()
        return {"message": "Transação atualizada com sucesso!", "transaction": updated_tx}

@router.patch("/transactions/{transaction_id}/toggle-paid", status_code=status.HTTP_200_OK)
def toggle_transaction_paid(
    transaction_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Alterna o status de liquidação (pago / pendente) de uma transação/conta.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id, is_paid FROM transactions WHERE id = %s;", (transaction_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada.")

        if current_user and existing["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")

        new_status = not bool(existing.get("is_paid", True))
        cursor.execute(
            "UPDATE transactions SET is_paid = %s WHERE id = %s RETURNING id, is_paid;",
            (new_status, transaction_id)
        )
        return {"message": f"Status atualizado para {'Liquidado' if new_status else 'Pendente'}.", "is_paid": new_status}

@router.get("/transactions/{user_id}/timeline", response_model=TimelineResponse, status_code=status.HTTP_200_OK)
def get_patrimonial_timeline(
    user_id: int,
    days: int = Query(30, ge=7, le=365, description="Janela de dias para a evolução"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Gera a série temporal de evolução patrimonial (gráfico da linha do tempo)
    calculando o saldo acumulado dia a dia com agregação SQL de alta performance.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            """
            SELECT 
                transaction_date::text AS day,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS daily_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS daily_expense
            FROM transactions
            WHERE user_id = %s
            GROUP BY transaction_date
            ORDER BY transaction_date ASC;
            """,
            (effective_user_id,)
        )
        rows = cursor.fetchall()

    points = []
    cumulative = 0.0

    for r in rows:
        inc = float(r["daily_income"])
        exp = float(r["daily_expense"])
        net = inc - exp
        cumulative += net
        points.append(TimelinePoint(
            date=r["day"],
            income=round(inc, 2),
            expense=round(exp, 2),
            daily_net=round(net, 2),
            cumulative_balance=round(cumulative, 2)
        ))

    starting_bal = points[0].cumulative_balance if points else 0.0
    ending_bal = points[-1].cumulative_balance if points else 0.0

    return TimelineResponse(
        points=points,
        starting_balance=round(starting_bal, 2),
        ending_balance=round(ending_bal, 2),
        total_days=len(points)
    )

@router.get("/transactions/{user_id}/bills", response_model=BillsResponse, status_code=status.HTTP_200_OK)
def get_bills_alerts(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retorna contas a pagar/receber com datas de vencimento categorizadas em:
    - Vencidas (overdue)
    - Vencendo Hoje (today)
    - Próximas (upcoming)
    - Pagas (paid)
    """
    effective_user_id = current_user["id"] if current_user else user_id
    today = date.today()

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            """
            SELECT id, user_id, type, amount, description, category, transaction_date, due_date, is_paid, tags
            FROM transactions
            WHERE user_id = %s AND due_date IS NOT NULL
            ORDER BY due_date ASC, id ASC;
            """,
            (effective_user_id,)
        )
        rows = cursor.fetchall()

    bills_list = []
    overdue_count = 0
    today_count = 0
    upcoming_count = 0
    total_pending = 0.0

    for r in rows:
        due = r["due_date"]
        is_paid = bool(r.get("is_paid", True))
        amount = float(r["amount"])
        days_diff = (due - today).days

        if is_paid:
            status_label = "paid"
            label = "Liquidada"
        elif days_diff < 0:
            status_label = "overdue"
            label = f"Atrasada há {abs(days_diff)} dia(s)"
            overdue_count += 1
            total_pending += amount
        elif days_diff == 0:
            status_label = "today"
            label = "Vence Hoje!"
            today_count += 1
            total_pending += amount
        else:
            status_label = "upcoming"
            label = f"Vence em {days_diff} dia(s)"
            upcoming_count += 1
            total_pending += amount

        bills_list.append(BillItem(
            id=r["id"],
            user_id=r["user_id"],
            type=r["type"],
            amount=round(amount, 2),
            description=r["description"],
            category=r["category"],
            transaction_date=r["transaction_date"],
            due_date=due,
            is_paid=is_paid,
            tags=r.get("tags", "") or "",
            status=status_label,
            days_diff=days_diff,
            label=label
        ))

    return BillsResponse(
        bills=bills_list,
        overdue_count=overdue_count,
        today_count=today_count,
        upcoming_count=upcoming_count,
        total_pending_amount=round(total_pending, 2)
    )

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
def delete_transaction(
    transaction_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Remove fisicamente um registo de transação com verificação de integridade e permissão.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id FROM transactions WHERE id = %s;", (transaction_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transação não encontrada."
            )

        if current_user and existing["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para remover esta transação."
            )

        cursor.execute("DELETE FROM transactions WHERE id = %s;", (transaction_id,))
        return {"message": "Transação removida com sucesso!"}

@router.get("/transactions/{user_id}/export", status_code=status.HTTP_200_OK)
def export_transactions(
    user_id: int,
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Exporta todo o histórico do utilizador nos formatos CSV ou JSON.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            """
            SELECT id, type, amount, description, category, transaction_date, tags, due_date, is_paid 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY transaction_date DESC, id DESC;
            """,
            (effective_user_id,)
        )
        transactions = cursor.fetchall()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["ID", "Tipo", "Valor", "Descricao", "Categoria", "Data", "Tags", "Vencimento", "Liquidado"])
        for tx in transactions:
            writer.writerow([
                tx["id"],
                "Receita" if tx["type"] == "income" else "Despesa",
                f"{float(tx['amount']):.2f}".replace(".", ","),
                tx["description"],
                tx["category"],
                tx["transaction_date"],
                tx.get("tags") or "",
                tx.get("due_date") or "",
                "Sim" if tx.get("is_paid") else "Nao"
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=finance_tracker_user_{effective_user_id}.csv"}
        )

    return {"transactions": transactions}
