import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt

from database import get_db_cursor
from schemas import UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api", tags=["Autenticação"])

# Configuração de Criptografia de Senhas com Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração do JWT
SECRET_KEY = os.getenv("JWT_SECRET", "finance-tracker-cyberpunk-secret-key-3000")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias de validade

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT id, name, email FROM users WHERE id = %s;", (int(user_id),))
            user = cursor.fetchone()
            return user
    except Exception:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    user = get_current_user_optional(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente, inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    """
    Regista um novo utilizador no sistema com senha criptografada via Bcrypt.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s;", (user.email.lower(),))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está registado no sistema."
            )
        
        hashed_password = pwd_context.hash(user.password)
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash) 
            VALUES (%s, %s, %s) 
            RETURNING id, name, email;
            """,
            (user.name.strip(), user.email.lower().strip(), hashed_password)
        )
        new_user = cursor.fetchone()
        return new_user

@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user: UserLogin):
    """
    Autentica as credenciais do utilizador e gera um token JWT de acesso seguro.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = %s;", 
            (user.email.lower().strip(),)
        )
        db_user = cursor.fetchone()
        
        if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas. Verifique o e-mail e a senha."
            )
        
        access_token = create_access_token(data={"sub": str(db_user["id"]), "email": db_user["email"]})
        
        return {
            "message": "Login efetuado com sucesso!",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user["id"],
                "name": db_user["name"],
                "email": db_user["email"]
            }
        }

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Retorna o perfil do utilizador autenticado a partir do token Bearer.
    """
    return current_user