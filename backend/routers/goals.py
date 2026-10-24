from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from database import get_db_cursor
from schemas import GoalCreate, GoalUpdate, GoalResponse
from routers.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Metas de Economia"])

@router.get("/goals/{user_id}", response_model=List[GoalResponse], status_code=status.HTTP_200_OK)
def get_user_goals(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retorna todas as metas financeiras do utilizador com percentual de progresso.
    """
    effective_user_id = current_user["id"] if current_user else user_id

    query = """
        SELECT id, user_id, title, target_amount, current_amount, target_date, created_at
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, (effective_user_id,))
        rows = cursor.fetchall()

    results = []
    for r in rows:
        target = float(r["target_amount"])
        current = float(r["current_amount"])
        pct = min(100.0, round((current / target) * 100, 1)) if target > 0 else 0.0

        results.append(GoalResponse(
            id=r["id"],
            user_id=r["user_id"],
            title=r["title"],
            target_amount=target,
            current_amount=current,
            target_date=r["target_date"],
            progress_percentage=pct
        ))

    return results

@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal: GoalCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Cria uma nova meta de poupança/economia.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória para criar metas."
        )

    user_id = current_user["id"]

    query = """
        INSERT INTO goals (user_id, title, target_amount, current_amount, target_date)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, user_id, title, target_amount, current_amount, target_date;
    """

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, (
            user_id, 
            goal.title.strip(), 
            goal.target_amount, 
            goal.current_amount or 0.0, 
            goal.target_date
        ))
        new_goal = cursor.fetchone()

    target = float(new_goal["target_amount"])
    current = float(new_goal["current_amount"])
    pct = min(100.0, round((current / target) * 100, 1)) if target > 0 else 0.0

    return GoalResponse(
        id=new_goal["id"],
        user_id=new_goal["user_id"],
        title=new_goal["title"],
        target_amount=target,
        current_amount=current,
        target_date=new_goal["target_date"],
        progress_percentage=pct
    )

@router.put("/goals/{goal_id}", response_model=GoalResponse, status_code=status.HTTP_200_OK)
def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Atualiza uma meta ou realiza um aporte financeiro (add_amount).
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id, title, target_amount, current_amount, target_date FROM goals WHERE id = %s;", (goal_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meta não encontrada."
            )

        if current_user and existing["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta meta."
            )

        new_title = goal_update.title.strip() if goal_update.title is not None else existing["title"]
        new_target = goal_update.target_amount if goal_update.target_amount is not None else float(existing["target_amount"])
        
        current_val = float(existing["current_amount"])
        if goal_update.current_amount is not None:
            current_val = goal_update.current_amount
        elif goal_update.add_amount is not None:
            current_val += goal_update.add_amount

        new_date = goal_update.target_date if goal_update.target_date is not None else existing["target_date"]

        cursor.execute(
            """
            UPDATE goals 
            SET title = %s, target_amount = %s, current_amount = %s, target_date = %s
            WHERE id = %s
            RETURNING id, user_id, title, target_amount, current_amount, target_date;
            """,
            (new_title, new_target, current_val, new_date, goal_id)
        )
        updated = cursor.fetchone()

    target = float(updated["target_amount"])
    current = float(updated["current_amount"])
    pct = min(100.0, round((current / target) * 100, 1)) if target > 0 else 0.0

    return GoalResponse(
        id=updated["id"],
        user_id=updated["user_id"],
        title=updated["title"],
        target_amount=target,
        current_amount=current,
        target_date=updated["target_date"],
        progress_percentage=pct
    )

@router.delete("/goals/{goal_id}", status_code=status.HTTP_200_OK)
def delete_goal(
    goal_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Remove uma meta financeira.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, user_id FROM goals WHERE id = %s;", (goal_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meta não encontrada."
            )

        if current_user and existing["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para remover esta meta."
            )

        cursor.execute("DELETE FROM goals WHERE id = %s;", (goal_id,))
        return {"message": "Meta removida com sucesso!"}
