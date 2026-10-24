"""
Modelos SQLAlchemy 2.0 e DDL idempotente do banco.

`init_db()` cria as tabelas ausentes e aplica migrações idempotentes para bancos
já existentes (criados por versões anteriores do projeto). A versão do schema fica
registrada na tabela `schema_version`, evitando reexecutar DDL a cada cold start
da função serverless.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.session import get_engine

SCHEMA_VERSION = 3
_SCHEMA_LOCK_KEY = 727274


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("idx_users_demo", "is_demo", "created_at"),)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))
    transaction_date: Mapped[date] = mapped_column(Date)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name="ck_transactions_type"),
        Index("idx_transactions_user_date", "user_id", text("transaction_date DESC")),
        Index("idx_transactions_category", "user_id", "category"),
        Index("idx_transactions_due_date", "user_id", "due_date", "is_paid"),
    )


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50))
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
        Index("idx_budgets_user", "user_id"),
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0"))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("idx_goals_user", "user_id"),)


class PushSubscription(Base):
    """Assinatura Web Push (um navegador/dispositivo) usada para lembretes de vencimento."""

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("idx_push_user", "user_id"),)


# Migrações para bancos criados por versões anteriores. Cada comando é idempotente
# e executado isoladamente (o asyncpg não aceita vários comandos por statement).
_MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE",
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS due_date DATE",
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT TRUE",
    "UPDATE transactions SET is_paid = TRUE WHERE is_paid IS NULL",
    "ALTER TABLE transactions ALTER COLUMN is_paid SET NOT NULL",
    # `tags` era VARCHAR (v2.2); passa a TEXT[] preservando as hashtags já gravadas.
    r"""
    DO $$
    DECLARE col_type text;
    BEGIN
        SELECT data_type INTO col_type FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'transactions' AND column_name = 'tags';
        IF col_type IS NULL THEN
            ALTER TABLE transactions ADD COLUMN tags TEXT[] NOT NULL DEFAULT '{}';
        ELSIF col_type <> 'ARRAY' THEN
            ALTER TABLE transactions ALTER COLUMN tags DROP DEFAULT;
            ALTER TABLE transactions ALTER COLUMN tags TYPE TEXT[] USING (
                array_remove(
                    regexp_split_to_array(
                        lower(replace(btrim(coalesce(tags, '')), '#', '')),
                        '\s+'
                    ),
                    ''
                )
            );
            UPDATE transactions SET tags = '{}' WHERE tags IS NULL;
            ALTER TABLE transactions ALTER COLUMN tags SET DEFAULT '{}';
            ALTER TABLE transactions ALTER COLUMN tags SET NOT NULL;
        END IF;
    END $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_transactions_tags ON transactions USING GIN (tags)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_due_date ON transactions (user_id, due_date, is_paid)",
)


async def init_db() -> None:
    """Cria/atualiza o schema de forma idempotente e segura contra cold starts concorrentes."""
    async with get_engine().begin() as conn:
        # Serializa instâncias concorrentes (liberado automaticamente ao fim da transação).
        await conn.exec_driver_sql(f"SELECT pg_advisory_xact_lock({_SCHEMA_LOCK_KEY})")
        await conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        current = (await conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM schema_version"))).scalar_one()
        if current >= SCHEMA_VERSION:
            return

        await conn.run_sync(Base.metadata.create_all)
        for statement in _MIGRATIONS:
            await conn.exec_driver_sql(statement)
        await conn.execute(text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": SCHEMA_VERSION})
