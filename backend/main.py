from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import init_db
from routers import auth, transactions

app = FastAPI(
    title="FinanceTracker API",
    description="API RESTful de controle financeiro pessoal desenvolvida em Python (FastAPI) e PostgreSQL.",
    version="1.1.0"
)

# Configuração de CORS para autorizar requisições do front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Executado no arranque do servidor FastAPI para garantir o DDL."""
    init_db()

@app.get("/", tags=["Health Check"])
def read_root():
    return {
        "status": "online",
        "system": "FinanceTracker API",
        "version": "1.1.0"
    }

# Registo dos Routers Modulares
app.include_router(auth.router)
app.include_router(transactions.router)