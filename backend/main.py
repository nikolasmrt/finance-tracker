import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import get_db_cursor
from models import init_db
from routers import auth, transactions, budgets, goals, cron

def get_real_client_ip(request: Request) -> str:
    """Extrai o IP real do cliente mesmo atrás de proxies ou CDNs da Vercel."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

# Rate Limiter contra ataques de força bruta e abusos
limiter = Limiter(key_func=get_real_client_ip, default_limits=["200/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado no arranque do servidor FastAPI para garantir o DDL e índices relacionais.
    """
    try:
        init_db()
        print("Banco de dados pronto para receber conexões Serverless.")
    except Exception as e:
        print(f"Alerta: Falha ao inicializar o banco de dados no arranque: {e}")
    yield

app = FastAPI(
    title="FinanceTracker API",
    description="API RESTful de controle financeiro pessoal avançado desenvolvida com FastAPI, Pydantic e PostgreSQL.",
    version="2.1.0",
    lifespan=lifespan
)

# Configuração do SlowAPI Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuração de CORS dinâmica e rígida
allowed_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
]

vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    allowed_origins.append(f"https://{vercel_url}")

custom_origin = os.getenv("FRONTEND_URL")
if custom_origin:
    allowed_origins.append(custom_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
@app.get("/api", tags=["Health Check"])
@app.get("/api/health", tags=["Health Check"])
def read_root():
    db_status = "offline"
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT 1;")
            if cursor.fetchone():
                db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "online",
        "system": "FinanceTracker API",
        "version": "2.1.0",
        "database": db_status
    }

# Registo dos Routers Modulares
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(cron.router)
