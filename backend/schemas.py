from pydantic import BaseModel, EmailStr
from datetime import date

# --- Schemas de Utilizadores ---

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

# --- Schemas de Transações Financeiras ---

class TransactionCreate(BaseModel):
    user_id: int
    type: str  # 'income' ou 'expense'
    amount: float
    description: str
    category: str
    transaction_date: date

class TransactionResponse(TransactionCreate):
    id: int

    class Config:
        from_attributes = True