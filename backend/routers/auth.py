from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from database import get_db_connection
from schemas import UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api", tags=["Autenticação"])

# Configuração com Bcrypt 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s;", (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está registado no sistema."
            )
        
        hashed_password = pwd_context.hash(user.password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email;",
            (user.name, user.email, hashed_password)
        )
        new_user = cursor.fetchone()
        conn.commit()
        return new_user
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao registar utilizador: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()

@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s;", (user.email,))
        db_user = cursor.fetchone()
        
        if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas. Verifique o e-mail e a senha."
            )
            
        return {
            "message": "Login efetuado com sucesso!",
            "user": {
                "id": db_user["id"],
                "name": db_user["name"],
                "email": db_user["email"]
            }
        }
    finally:
        cursor.close()
        conn.close()