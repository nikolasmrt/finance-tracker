from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import date
from typing import Optional, Dict, Any, List

# --- Schemas de Utilizadores ---

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

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