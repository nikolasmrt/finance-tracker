from datetime import date, timedelta
from typing import Optional, List
import io
import csv
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse

from database import get_db_cursor
from schemas import (
    TransactionCreate, 
    TransactionUpdate, 
    TransactionResponse,
    TransactionsSummary,
    CategoryBreakdownItem,
    SmartForecast
)
from routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Transações"])

@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(
    tx: TransactionCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Cria uma nova movimentação financeira (receita ou despesa).
    """
    effective_user_id = current_user["id"] if current_user else tx.user_id
    tx_date = tx.transaction_date or date.today()

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO transactions (user_id, type, amount, description, category, transaction_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, type, amount, description, category, transaction_date;
            """,
            (effective_user_id, tx.type, tx.amount, tx.description.strip(), tx.category.strip(), tx_date)
        )
        new_tx = cursor.fetchone()
        return {"message": "Transação criada com sucesso!", "transaction": new_tx}

@router.get("/transactions/{user_id}", status_code=status.HTTP_200_OK)
def get_transactions(
    user_id: int,
    type: Optional[str] = Query(None, description="Filtrar por tipo: 'income' ou 'expense'"),
    category: Optional[str] = Query(None, description="Filtrar por categoria específica"),
    search: Optional[str] = Query(None, description="Busca textual na descrição"),
    start_date: Optional[date] = Query(None, description="Data inicial do filtro"),
    end_date: Optional[date] = Query(None, description="Data final do filtro"),
    limit: int = Query(200, ge=1, le=1000, description="Limite de registros a retornar")
):
    """
    Lista o histórico de movimentações financeiras de um utilizador,
    suportando filtros avançados por tipo, categoria, intervalo de datas e busca por descrição.
    """
    query = """
        SELECT id, user_id, type, amount, description, category, transaction_date 
        FROM transactions 
        WHERE user_id = %s
    """
    params = [user_id]

    if type in ("income", "expense"):
        query += " AND type = %s"
        params.append(type)

    if category:
        query += " AND category = %s"
        params.append(category)

    if search:
        query += " AND description ILIKE %s"
        params.append(f"%{search.strip()}%")

    if start_date:
        query += " AND transaction_date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND transaction_date <= %s"
        params.append(end_date)

    query += " ORDER BY transaction_date DESC, id DESC LIMIT %s;"
    params.append(limit)

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, tuple(params))
        transactions = cursor.fetchall()
        return {"transactions": transactions, "total_count": len(transactions)}

@router.get("/transactions/{user_id}/summary", response_model=TransactionsSummary)
def get_transactions_summary(user_id: int):
    """
    Retorna o resumo consolidado do utilizador com totais, balanço,
    distribuição por categoria e cálculo de Previsão Inteligente para 30 dias.
    """
    with get_db_cursor(commit=False) as cursor:
        # Busca todas as transações do utilizador
        cursor.execute(
            """
            SELECT id, type, amount, description, category, transaction_date 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY transaction_date ASC;
            """,
            (user_id,)
        )
        transactions = cursor.fetchall()

    total_income = 0.0
    total_expense = 0.0
    cat_map = {}
    dates = []

    for tx in transactions:
        amt = float(tx["amount"])
        cat = tx["category"]
        tx_type = tx["type"]
        tx_date = tx["transaction_date"]
        dates.append(tx_date)

        if cat not in cat_map:
            cat_map[cat] = {"income": 0.0, "expense": 0.0, "count": 0}

        cat_map[cat]["count"] += 1

        if tx_type == "income":
            total_income += amt
            cat_map[cat]["income"] += amt
        else:
            total_expense += amt
            cat_map[cat]["expense"] += amt

    net_balance = round(total_income - total_expense, 2)

    categories_list = []
    for cat_name, stats in cat_map.items():
        categories_list.append(CategoryBreakdownItem(
            category=cat_name,
            total_income=round(stats["income"], 2),
            total_expense=round(stats["expense"], 2),
            net=round(stats["income"] - stats["expense"], 2),
            count=stats["count"]
        ))
    categories_list.sort(key=lambda c: (c.total_expense + c.total_income), reverse=True)

    # --- Previsão Inteligente para 30 dias ---
    days_span = 30
    if len(dates) >= 2:
        diff_days = max(1, (dates[-1] - dates[0]).days)
        days_span = min(max(diff_days, 7), 90)

    daily_avg_expense = total_expense / days_span if total_expense > 0 else 0.0
    daily_avg_income = total_income / days_span if total_income > 0 else 0.0

    projected_expense_30d = round(daily_avg_expense * 30, 2)
    projected_income_30d = round(daily_avg_income * 30, 2)
    projected_balance_30d = round(net_balance + projected_income_30d - projected_expense_30d, 2)

    savings_rate = round(((total_income - total_expense) / total_income) * 100, 1) if total_income > 0 else 0.0

    if not transactions:
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
        forecast_msg = f"Ritmo de gastos moderado. Controle despesas para manter o saldo positivo nos próximos 30 dias."

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
        transactions_count=len(transactions),
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
    Atualiza os campos de uma movimentação financeira existente.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id FROM transactions WHERE id = %s;", (transaction_id,))
        existing_tx = cursor.fetchone()

        if not existing_tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transação não encontrada."
            )

        # Se houver usuário autenticado no token, garante que só altera o próprio registro
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
            RETURNING id, user_id, type, amount, description, category, transaction_date;
        """
        cursor.execute(update_query, tuple(params))
        updated_tx = cursor.fetchone()
        return {"message": "Transação atualizada com sucesso!", "transaction": updated_tx}

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
def delete_transaction(
    transaction_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Remove fisicamente um registo de transação com verificação de permissão.
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
    format: str = Query("csv", pattern="^(csv|json)$")
):
    """
    Exporta todo o histórico do utilizador nos formatos CSV ou JSON.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            """
            SELECT id, type, amount, description, category, transaction_date 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY transaction_date DESC, id DESC;
            """,
            (user_id,)
        )
        transactions = cursor.fetchall()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["ID", "Tipo", "Valor", "Descricao", "Categoria", "Data"])
        for tx in transactions:
            writer.writerow([
                tx["id"],
                "Receita" if tx["type"] == "income" else "Despesa",
                f"{float(tx['amount']):.2f}".replace(".", ","),
                tx["description"],
                tx["category"],
                tx["transaction_date"]
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=finance_tracker_user_{user_id}.csv"}
        )

    return {"transactions": transactions}