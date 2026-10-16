from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import get_db_cursor
from models import init_db
from routers import auth, transactions

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado no arranque do servidor FastAPI para garantir o DDL e índices relacionais.
    """
    try:
        init_db()
        print("Banco de dados pronto para receber conexões.")
    except Exception as e:
        print(f"Alerta: Falha ao inicializar o banco de dados no arranque: {e}")
    yield

app = FastAPI(
    title="FinanceTracker API",
    description="API RESTful de controle financeiro pessoal avançado desenvolvida com FastAPI, Pydantic e PostgreSQL.",
    version="2.0.0",
    lifespan=lifespan
)

# Configuração de CORS aberta e segura para desenvolvimento e produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "version": "2.0.0",
        "database": db_status
    }

# Registo dos Routers Modulares
app.include_router(auth.router)
app.include_router(transactions.router)