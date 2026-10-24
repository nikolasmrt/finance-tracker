from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import date
from typing import Optional, Dict, Any, List

# --- Schemas de Utilizadores & Sessão ---

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nome completo do utilizador")
    email: EmailStr = Field(..., description="E-mail único de acesso")
    password: str = Field(..., min_length=6, description="Senha de acesso com no mínimo 6 caracteres")

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    is_demo: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class DemoSessionResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_demo: bool = True

# --- Schemas de Transações Financeiras ---

class TransactionCreate(BaseModel):
    user_id: int = Field(..., description="ID do utilizador proprietário")
    type: str = Field(..., description="Tipo de movimentação: 'income' ou 'expense'")
    amount: float = Field(..., gt=0, description="O valor deve ser estritamente maior que zero")
    description: str = Field(..., min_length=1, max_length=255, description="Descrição da movimentação")
    category: str = Field(..., min_length=1, max_length=50, description="Categoria da movimentação")
    transaction_date: Optional[date] = Field(default=None, description="Data da transação (padrão: hoje)")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("income", "expense"):
            raise ValueError("O tipo de movimentação deve ser 'income' (depósito) ou 'expense' (gasto).")
        return v

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    transaction_date: Optional[date] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("income", "expense"):
            raise ValueError("O tipo de movimentação deve ser 'income' ou 'expense'.")
        return v

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    type: str
    amount: float
    description: str
    category: str
    transaction_date: date

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int

class PaginatedTransactionsResponse(BaseModel):
    transactions: List[TransactionResponse]
    pagination: PaginationMeta

# --- Schemas de Resumo Analítico e Previsão Inteligente ---

class CategoryBreakdownItem(BaseModel):
    category: str
    total_income: float
    total_expense: float
    net: float
    count: int

class SmartForecast(BaseModel):
    daily_average_expense: float
    daily_average_income: float
    projected_expense_30d: float
    projected_income_30d: float
    projected_balance_30d: float
    savings_rate: float
    status: str
    message: str

class TransactionsSummary(BaseModel):
    total_deposits: float
    total_expenses: float
    net_balance: float
    transactions_count: int
    categories: List[CategoryBreakdownItem]
    forecast: SmartForecast

# --- Schemas de Orçamentos por Categoria (Budgets) ---

class BudgetCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Nome da categoria")
    monthly_limit: float = Field(..., gt=0, description="Teto máximo de gasto mensal")

class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    category: str
    monthly_limit: float
    spent_this_month: float = 0.0
    percentage_used: float = 0.0
    status: str = "safe"  # safe (<70%), warning (70-90%), exceeded (>90%)

# --- Schemas de Metas de Economia (Savings Goals) ---

class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Título da meta")
    target_amount: float = Field(..., gt=0, description="Valor total almejado")
    current_amount: Optional[float] = Field(default=0.0, ge=0, description="Valor inicial já poupado")
    target_date: Optional[date] = Field(default=None, description="Data estimada para conclusão")

class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_amount: Optional[float] = Field(default=None, gt=0)
    current_amount: Optional[float] = Field(default=None, ge=0)
    add_amount: Optional[float] = Field(default=None, gt=0, description="Aporte rápido na meta")
    target_date: Optional[date] = None

class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    title: str
    target_amount: float
    current_amount: float
    target_date: Optional[date] = None
    progress_percentage: float = 0.0
