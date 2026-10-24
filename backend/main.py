"""
Ponto de entrada da API FastAPI — FinanceTracker v3.0 (Clean Architecture & Serverless Ready).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.core.security import limiter
from app.db.session import ensure_schema, get_engine
from app.routers import auth, budgets, cron, goals, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o esquema relacional e migrações idempotentes no arranque."""
    try:
        await ensure_schema()
    except Exception as exc:
        print(f"Alerta: Falha ao inicializar o banco de dados no arranque: {exc}")
    yield


app = FastAPI(
    title="FinanceTracker API",
    description=(
        "API RESTful de controle financeiro pessoal avançado com FastAPI, "
        "SQLAlchemy 2.0 Assíncrono, Pydantic V2, Cookies HttpOnly e PostgreSQL."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# Rate Limiter contra ataques de força bruta e abusos
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Política de CORS restrita (localhost em dev + domínios Vercel autorizados)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.get("/", tags=["Health Check"])
@app.get("/api", tags=["Health Check"])
@app.get("/api/health", tags=["Health Check"])
async def health_check():
    db_status = "offline"
    try:
        await ensure_schema()
        async with get_engine().connect() as conn:
            result = await conn.scalar(text("SELECT 1"))
            if result == 1:
                db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "online",
        "system": "FinanceTracker API",
        "version": settings.app_version,
        "database": db_status,
    }


# Registo dos Routers Modulares
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(cron.router)
