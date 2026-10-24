"""Modo Convidado: criação de perfis de demonstração com dados fictícios e limpeza de perfis expirados."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.models import Budget, Goal, Transaction, User

DEMO_NAME = "Visitante Convidado"


def demo_cutoff() -> datetime:
    """Perfis de demonstração criados antes deste instante (UTC, sem fuso) estão expirados."""
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=settings.demo_ttl_hours)


async def purge_expired_demo_users(session: AsyncSession) -> int:
    """Remove convidados expirados; transações, orçamentos, metas e assinaturas caem em cascata."""
    result = await session.execute(delete(User).where(User.is_demo.is_(True), User.created_at < demo_cutoff()))
    return result.rowcount or 0


async def create_demo_user(session: AsyncSession) -> User:
    """Cria o convidado com uma senha aleatória (impossível de usar para login manual)."""
    user = User(
        name=DEMO_NAME,
        email=f"guest_{uuid.uuid4().hex[:12]}@demo.local",
        password_hash=await hash_password(uuid.uuid4().hex),
        is_demo=True,
    )
    session.add(user)
    await session.flush()
    session.add_all(_demo_records(user.id, date.today()))
    return user


def _demo_records(user_id: int, today: date) -> list:
    # Despesas das categorias com orçamento ficam dentro do mês corrente para que as barras de progresso mostrem consumo.
    budgeted = {"Alimentação", "Moradia", "Lazer", "Transporte"}
    days_into_month = today.day - 1

    def tx(kind, amount, description, category, days_ago, tags, due_offset=None, paid=True):
        if kind == "expense" and category in budgeted:
            days_ago = min(days_ago, days_into_month)
        return Transaction(
            user_id=user_id,
            type=kind,
            amount=Decimal(amount),
            description=description,
            category=category,
            transaction_date=today - timedelta(days=days_ago),
            tags=tags,
            due_date=None if due_offset is None else today + timedelta(days=due_offset),
            is_paid=paid,
        )

    transactions = [
        tx("income", "6500.00", "Salário Tech Lead", "Trabalho", 20, ["salario", "tech"]),
        tx("income", "1200.00", "Freelance API FastAPI", "Trabalho", 9, ["freela", "dev"]),
        tx("income", "450.00", "Dividendos FIIs e Ações", "Investimentos", 12, ["dividendos", "passivo"]),
        tx("expense", "1950.00", "Aluguel e Condomínio", "Moradia", 18, ["fixo", "casa"], -18),
        tx("expense", "680.50", "Supermercado Mensal", "Alimentação", 11, ["mercado", "essencial"]),
        tx("expense", "240.00", "Combustível e Uber", "Transporte", 7, ["carro"]),
        tx("expense", "189.90", "Assinatura Cloud e Cursos", "Estudo", 15, ["cloud", "carreira"]),
        tx("expense", "210.00", "Jantar no Lounge", "Lazer", 4, ["restaurante", "viagem2026"]),
        tx("expense", "160.00", "Farmácia e Vitaminas", "Saúde", 2, ["saude"]),
        # Contas com alerta de vencimento: hoje, atrasada e a vencer.
        tx("expense", "129.90", "Fatura Internet Fibra", "Moradia", 0, ["internet", "fixo"], 0, False),
        tx("expense", "79.90", "Assinatura de Streaming", "Lazer", 3, ["streaming"], -2, False),
        tx("expense", "350.00", "Plano de Saúde", "Saúde", 0, ["convenio"], 4, False),
        tx("expense", "420.00", "Cartão de Crédito", "Outros", 0, ["cartao"], 9, False),
    ]
    budgets = [
        Budget(user_id=user_id, category=category, monthly_limit=Decimal(limit))
        for category, limit in (("Alimentação", "1100.00"), ("Moradia", "2200.00"), ("Lazer", "500.00"), ("Transporte", "400.00"))
    ]
    goals = [
        Goal(user_id=user_id, title=title, target_amount=Decimal(target), current_amount=Decimal(current), target_date=today + timedelta(days=days))
        for title, target, current, days in (
            ("Reserva de Emergência", "25000.00", "18500.00", 180),
            ("Notebook Novo", "10000.00", "6400.00", 90),
            ("Viagem ao Japão", "15000.00", "4200.00", 240),
        )
    ]
    return [*transactions, *budgets, *goals]
