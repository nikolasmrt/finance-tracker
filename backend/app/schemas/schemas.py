"""Schemas Pydantic V2 estritos de entrada e saída da API."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from app.core.sanitize import clean_text, normalize_tags

# Valores monetários trafegam como Decimal (exatidão) e saem como número no JSON.
Money = Annotated[
    Decimal,
    Field(max_digits=10, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]
PositiveMoney = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]
CleanStr = Annotated[str, Field(min_length=1)]

TransactionType = Literal["income", "expense"]


class StrictInput(BaseModel):
    """Base dos payloads de entrada: campos desconhecidos são ignorados (clientes antigos não quebram)."""

    model_config = ConfigDict(extra="ignore")


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _sanitized(value: str) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        raise ValueError("O texto não pode ficar vazio após a sanitização.")
    return cleaned


# --- Autenticação ---------------------------------------------------------------------


class UserCreate(StrictInput):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="Bcrypt limita a 72 bytes.")

    _clean_name = field_validator("name")(lambda cls, v: _sanitized(v))


class UserLogin(StrictInput):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(OutputModel):
    id: int
    name: str
    email: str
    is_demo: bool = False


class AuthResponse(BaseModel):
    message: str
    user: UserOut


# --- Transações -----------------------------------------------------------------------


class TransactionCreate(StrictInput):
    type: TransactionType
    amount: PositiveMoney
    description: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=50)
    transaction_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    due_date: date | None = None
    is_paid: bool = True

    _clean_text = field_validator("description", "category")(lambda cls, v: _sanitized(v))

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value):
        return normalize_tags(value)


class TransactionUpdate(StrictInput):
    """Atualização parcial: apenas campos enviados são alterados; `due_date: null` limpa o vencimento."""

    type: TransactionType | None = None
    amount: PositiveMoney | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    transaction_date: date | None = None
    tags: list[str] | None = None
    due_date: date | None = None
    is_paid: bool | None = None

    @field_validator("description", "category")
    @classmethod
    def _clean_optional_text(cls, value):
        return None if value is None else _sanitized(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value):
        return None if value is None else normalize_tags(value)

    @model_validator(mode="after")
    def _reject_null_required_fields(self):
        for field in ("type", "amount", "description", "category", "transaction_date", "tags", "is_paid"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"O campo '{field}' não pode ser nulo.")
        return self


class TransactionOut(OutputModel):
    id: int
    user_id: int
    type: TransactionType
    amount: Money
    description: str
    category: str
    transaction_date: date
    tags: list[str] = Field(default_factory=list)
    due_date: date | None = None
    is_paid: bool = True


class TransactionEnvelope(BaseModel):
    message: str
    transaction: TransactionOut


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int
    current_page: int


class PaginatedTransactions(BaseModel):
    transactions: list[TransactionOut]
    pagination: PaginationMeta


class TagUsage(BaseModel):
    tag: str
    uses: int


# --- Resumo, previsão, linha do tempo e contas ----------------------------------------


class CategoryBreakdown(BaseModel):
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
    status: Literal["positive", "warning", "critical", "neutral"]
    message: str


class TransactionsSummary(BaseModel):
    total_deposits: float
    total_expenses: float
    net_balance: float
    transactions_count: int
    income_count: int
    expense_count: int
    pending_income: float
    pending_expenses: float
    pending_count: int
    categories: list[CategoryBreakdown]
    forecast: SmartForecast


class TimelinePoint(BaseModel):
    date: date
    income: float
    expense: float
    daily_net: float
    cumulative_balance: float


class TimelineResponse(BaseModel):
    days: int
    points: list[TimelinePoint]
    starting_balance: float
    ending_balance: float
    total_days: int


class BillItem(BaseModel):
    id: int
    type: TransactionType
    amount: float
    description: str
    category: str
    due_date: date
    is_paid: bool
    tags: list[str] = Field(default_factory=list)
    status: Literal["overdue", "today", "upcoming", "paid"]
    days_diff: int
    label: str


class BillsResponse(BaseModel):
    bills: list[BillItem]
    overdue_count: int
    today_count: int
    upcoming_count: int
    total_pending_amount: float


# --- Orçamentos e metas ---------------------------------------------------------------


class BudgetCreate(StrictInput):
    category: str = Field(min_length=1, max_length=50)
    monthly_limit: PositiveMoney

    _clean_category = field_validator("category")(lambda cls, v: _sanitized(v))


class BudgetOut(OutputModel):
    id: int
    user_id: int
    category: str
    monthly_limit: Money
    spent_this_month: float = 0.0
    percentage_used: float = 0.0
    status: Literal["safe", "warning", "exceeded"] = "safe"  # safe < 80% <= warning < 100% <= exceeded


class GoalCreate(StrictInput):
    title: str = Field(min_length=1, max_length=100)
    target_amount: PositiveMoney
    current_amount: Money = Field(default=Decimal("0"), ge=0)
    target_date: date | None = None

    _clean_title = field_validator("title")(lambda cls, v: _sanitized(v))


class GoalUpdate(StrictInput):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount: PositiveMoney | None = None
    current_amount: Money | None = Field(default=None, ge=0)
    add_amount: PositiveMoney | None = Field(default=None, description="Aporte rápido somado ao valor atual.")
    target_date: date | None = None

    @field_validator("title")
    @classmethod
    def _clean_optional_title(cls, value):
        return None if value is None else _sanitized(value)


class GoalOut(OutputModel):
    id: int
    user_id: int
    title: str
    target_amount: Money
    current_amount: Money
    target_date: date | None = None
    progress_percentage: float = 0.0


# --- Web Push -------------------------------------------------------------------------


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscribeIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048, pattern=r"^https://")
    keys: PushKeys


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048)


class PushConfigOut(BaseModel):
    enabled: bool
    public_key: str | None = None
