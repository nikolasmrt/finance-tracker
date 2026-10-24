import os
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt

from database import get_db_cursor
from schemas import UserCreate, UserLogin, UserResponse, DemoSessionResponse

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

def set_auth_cookie(response: Response, token: str, request: Request):
    """
    Grava o token JWT em um cookie HTTP-Only, Secure e SameSite=Lax,
    blindando a aplicação contra ataques de XSS no navegador.
    """
    is_secure = (
        request.url.scheme == "https" 
        or os.getenv("VERCEL") == "1" 
        or os.getenv("ENVIRONMENT") == "production"
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/"
    )

def clear_auth_cookie(response: Response):
    response.delete_cookie(key="access_token", path="/")

def extract_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    # 1. Prioriza Cookie HTTP-Only seguro
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    # 2. Fallback para cabeçalho Authorization: Bearer <token>
    if credentials:
        return credentials.credentials
    return None

def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    token = extract_token_from_request(request, credentials)
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT id, name, email, is_demo FROM users WHERE id = %s;", (int(user_id),))
            user = cursor.fetchone()
            return user
    except Exception:
        return None

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    user = get_current_user_optional(request, credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não autenticada ou expirada. Faça login para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, request: Request, response: Response):
    """
    Regista um novo utilizador no sistema com senha criptografada via Bcrypt
    e grava cookie de autenticação seguro.
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s;", (user.email.lower().strip(),))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está registado no sistema."
            )
        
        hashed_password = pwd_context.hash(user.password)
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, is_demo) 
            VALUES (%s, %s, %s, FALSE) 
            RETURNING id, name, email, is_demo;
            """,
            (user.name.strip(), user.email.lower().strip(), hashed_password)
        )
        new_user = cursor.fetchone()

        # Emite e grava cookie imediatamente
        token = create_access_token(data={"sub": str(new_user["id"]), "email": new_user["email"]})
        set_auth_cookie(response, token, request)
        return new_user

@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user: UserLogin, request: Request, response: Response):
    """
    Autentica as credenciais do utilizador, gera token JWT e grava cookie HTTP-Only.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            "SELECT id, name, email, password_hash, is_demo FROM users WHERE email = %s;", 
            (user.email.lower().strip(),)
        )
        db_user = cursor.fetchone()
        
        if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas. Verifique o e-mail e a senha."
            )
        
        access_token = create_access_token(data={"sub": str(db_user["id"]), "email": db_user["email"]})
        set_auth_cookie(response, access_token, request)
        
        return {
            "message": "Login efetuado com sucesso!",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user["id"],
                "name": db_user["name"],
                "email": db_user["email"],
                "is_demo": bool(db_user.get("is_demo", False))
            }
        }

@router.post("/demo", response_model=DemoSessionResponse, status_code=status.HTTP_201_CREATED)
def create_demo_session(request: Request, response: Response):
    """
    Modo Convidado 1-Click:
    Cria uma sessão de demonstração temporária, pré-povoada com transações,
    orçamentos e metas fictícias para teste imediato na Vercel.
    """
    demo_id = uuid.uuid4().hex[:8]
    demo_email = f"guest_{demo_id}@demo.local"
    demo_name = f"Visitante Convidado"
    demo_password_hash = pwd_context.hash("demo123456")

    today = date.today()

    with get_db_cursor(commit=True) as cursor:
        # Limpeza preventiva de contas demo muito antigas (> 6 horas)
        cursor.execute("DELETE FROM users WHERE is_demo = TRUE AND created_at < NOW() - INTERVAL '6 hours';")

        # Cria usuário demo
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, is_demo)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id, name, email, is_demo;
            """,
            (demo_name, demo_email, demo_password_hash)
        )
        demo_user = cursor.fetchone()
        user_id = demo_user["id"]

        # Popula transações realistas
        demo_transactions = [
            (user_id, "income", 6500.00, "Salário Tech Lead", "Trabalho", today - timedelta(days=6)),
            (user_id, "income", 1200.00, "Freelance API FastAPI", "Trabalho", today - timedelta(days=2)),
            (user_id, "income", 450.00, "Dividendos FIIs & Ações", "Investimentos", today - timedelta(days=4)),
            (user_id, "expense", 1950.00, "Aluguel & Condomínio", "Moradia", today - timedelta(days=5)),
            (user_id, "expense", 680.50, "Supermercado Mensal", "Alimentação", today - timedelta(days=4)),
            (user_id, "expense", 240.00, "Combustível / Uber", "Transporte", today - timedelta(days=3)),
            (user_id, "expense", 189.90, "Assinatura Cloud & Cursos", "Estudo", today - timedelta(days=5)),
            (user_id, "expense", 210.00, "Jantar Cyberpunk Lounge", "Lazer", today - timedelta(days=2)),
            (user_id, "expense", 160.00, "Farmácia e Vitaminas", "Saúde", today - timedelta(days=1)),
        ]

        for tx in demo_transactions:
            cursor.execute(
                """
                INSERT INTO transactions (user_id, type, amount, description, category, transaction_date)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                tx
            )

        # Popula orçamentos mensais
        demo_budgets = [
            (user_id, "Alimentação", 1100.00),
            (user_id, "Moradia", 2200.00),
            (user_id, "Lazer", 500.00),
            (user_id, "Transporte", 400.00)
        ]
        for b in demo_budgets:
            cursor.execute(
                """
                INSERT INTO budgets (user_id, category, monthly_limit)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, category) DO NOTHING;
                """,
                b
            )

        # Popula metas de economia
        demo_goals = [
            (user_id, "Reserva de Emergência 6M", 25000.00, 18500.00, today + timedelta(days=180)),
            (user_id, "Setup Gamer Workstation", 10000.00, 6400.00, today + timedelta(days=90)),
            (user_id, "Viagem Tóquio Cyberpunk", 15000.00, 4200.00, today + timedelta(days=240)),
        ]
        for g in demo_goals:
            cursor.execute(
                """
                INSERT INTO goals (user_id, title, target_amount, current_amount, target_date)
                VALUES (%s, %s, %s, %s, %s);
                """,
                g
            )

    token = create_access_token(data={"sub": str(user_id), "email": demo_email, "is_demo": True})
    set_auth_cookie(response, token, request)

    return {
        "message": "Sessão de demonstração inicializada com sucesso!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": demo_name,
            "email": demo_email,
            "is_demo": True
        },
        "is_demo": True
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout_user(response: Response):
    """
    Encerra a sessão removendo o cookie de autenticação HTTP-Only.
    """
    clear_auth_cookie(response)
    return {"message": "Sessão encerrada com sucesso!"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Retorna o perfil do utilizador autenticado a partir do Cookie HTTP-Only ou Bearer token.
    """
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "is_demo": bool(current_user.get("is_demo", False))
    }
