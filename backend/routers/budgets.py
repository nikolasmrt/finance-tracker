from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from database import get_db_cursor
from schemas import BudgetCreate, BudgetResponse
from routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Orçamentos"])

@router.get("/budgets/{user_id}", response_model=List[BudgetResponse], status_code=status.HTTP_200_OK)
def get_user_budgets(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retorna os limites de orçamento por categoria do utilizador,
    calculando o total já gasto no mês corrente e a percentagem atingida.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    query = """
        SELECT 
            b.id,
            b.user_id,
            b.category,
            b.monthly_limit,
            COALESCE(SUM(t.amount), 0) AS spent_this_month
        FROM budgets b
        LEFT JOIN transactions t ON t.user_id = b.user_id 
            AND t.category = b.category 
            AND t.type = 'expense'
            AND t.transaction_date >= date_trunc('month', CURRENT_DATE)
            AND t.transaction_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
        WHERE b.user_id = %s
        GROUP BY b.id, b.user_id, b.category, b.monthly_limit
        ORDER BY b.category ASC;
    """

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, (effective_user_id,))
        rows = cursor.fetchall()

    results = []
    for r in rows:
        limit = float(r["monthly_limit"])
        spent = float(r["spent_this_month"])
        pct = round((spent / limit) * 100, 1) if limit > 0 else 0.0

        if pct >= 100.0:
            status_val = "exceeded"
        elif pct >= 80.0:
            status_val = "warning"
        else:
            status_val = "safe"

        results.append(BudgetResponse(
            id=r["id"],
            user_id=r["user_id"],
            category=r["category"],
            monthly_limit=limit,
            spent_this_month=spent,
            percentage_used=pct,
            status=status_val
        ))

    return results

@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def set_category_budget(
    budget: BudgetCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Define ou atualiza (upsert) o teto orçamentário mensal para uma categoria.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória para configurar orçamentos."
        )

    user_id = current_user["id"]
    cat = budget.category.strip()

    query = """
        INSERT INTO budgets (user_id, category, monthly_limit)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category) 
        DO UPDATE SET monthly_limit = EXCLUDED.monthly_limit
        RETURNING id, user_id, category, monthly_limit;
    """

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, (user_id, cat, budget.monthly_limit))
        saved = cursor.fetchone()

        # Calcula o gasto do mês atual para a resposta imediata
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS spent
            FROM transactions
            WHERE user_id = %s 
              AND category = %s 
              AND type = 'expense'
              AND transaction_date >= date_trunc('month', CURRENT_DATE)
              AND transaction_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month';
            """,
            (user_id, cat)
        )
        spent_row = cursor.fetchone()
        spent = float(spent_row["spent"]) if spent_row else 0.0

    limit = float(saved["monthly_limit"])
    pct = round((spent / limit) * 100, 1) if limit > 0 else 0.0
    status_val = "exceeded" if pct >= 100.0 else ("warning" if pct >= 80.0 else "safe")

    return BudgetResponse(
        id=saved["id"],
        user_id=saved["user_id"],
        category=saved["category"],
        monthly_limit=limit,
        spent_this_month=spent,
        percentage_used=pct,
        status=status_val
    )

@router.delete("/budgets/{budget_id}", status_code=status.HTTP_200_OK)
def delete_budget(
    budget_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Remove uma regra de orçamento de categoria.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id FROM budgets WHERE id = %s;", (budget_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orçamento não encontrado."
            )

        if current_user and existing["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para remover este orçamento."
            )

        cursor.execute("DELETE FROM budgets WHERE id = %s;", (budget_id,))
        return {"message": "Orçamento removido com sucesso!"}
