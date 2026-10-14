from fastapi import APIRouter, HTTPException, status
from database import get_db_connection
from schemas import TransactionCreate

router = APIRouter(prefix="/api", tags=["Transações"])

@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(tx: TransactionCreate):
    if tx.type not in ["income", "expense"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O tipo de transação deve ser 'income' ou 'expense'."
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO transactions (user_id, type, amount, description, category, transaction_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, type, amount, description, category, transaction_date;
            """,
            (tx.user_id, tx.type, tx.amount, tx.description, tx.category, tx.transaction_date)
        )
        new_tx = cursor.fetchone()
        conn.commit()
        return {"message": "Transação criada com sucesso!", "transaction": new_tx}
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registar transação: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()

@router.get("/transactions/{user_id}", status_code=status.HTTP_200_OK)
def get_transactions(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, user_id, type, amount, description, category, transaction_date 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY transaction_date DESC, id DESC;
            """,
            (user_id,)
        )
        transactions = cursor.fetchall()
        return {"transactions": transactions}
    finally:
        cursor.close()
        conn.close()

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
def delete_transaction(transaction_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM transactions WHERE id = %s;", (transaction_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transação não encontrada."
            )
            
        cursor.execute("DELETE FROM transactions WHERE id = %s;", (transaction_id,))
        conn.commit()
        return {"message": "Transação removida com sucesso!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover transação: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()