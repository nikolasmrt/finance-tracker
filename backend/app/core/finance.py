"""Regras de negócio puras (sem I/O): previsão, status de contas, orçamentos, metas e linha do tempo."""
from datetime import date, timedelta

BUDGET_WARNING_PCT = 80.0
BUDGET_EXCEEDED_PCT = 100.0
FORECAST_MIN_DAYS = 7
FORECAST_MAX_DAYS = 90


def percentage(part: float, whole: float, cap: float | None = None) -> float:
    if whole <= 0:
        return 0.0
    value = round(part / whole * 100, 1)
    return min(cap, value) if cap is not None else value


def budget_status(used_pct: float) -> str:
    if used_pct >= BUDGET_EXCEEDED_PCT:
        return "exceeded"
    if used_pct >= BUDGET_WARNING_PCT:
        return "warning"
    return "safe"


def build_forecast(
    total_income: float,
    total_expense: float,
    first_date: date | None,
    last_date: date | None,
    transactions_count: int,
) -> dict:
    """Projeta os próximos 30 dias a partir da média diária observada (janela de 7 a 90 dias)."""
    span_days = 30
    if first_date and last_date:
        span_days = min(max((last_date - first_date).days, FORECAST_MIN_DAYS), FORECAST_MAX_DAYS)

    daily_expense = total_expense / span_days if total_expense > 0 else 0.0
    daily_income = total_income / span_days if total_income > 0 else 0.0
    projected_expense = round(daily_expense * 30, 2)
    projected_income = round(daily_income * 30, 2)

    net_balance = round(total_income - total_expense, 2)
    projected_balance = round(net_balance + projected_income - projected_expense, 2)
    savings_rate = round((total_income - total_expense) / total_income * 100, 1) if total_income > 0 else 0.0

    if transactions_count == 0:
        status, message = "neutral", "Adicione as suas primeiras movimentações para gerar projeções analíticas."
    elif projected_balance < 0:
        status, message = "critical", "Atenção: no ritmo atual de gastos, o saldo pode ficar negativo nos próximos 30 dias."
    elif projected_balance >= net_balance and net_balance >= 0:
        status = "positive"
        message = f"Tendência favorável! Taxa de poupança estimada de {max(0.0, savings_rate)}%."
    else:
        status, message = "warning", "Ritmo de gastos moderado. Controle as despesas para manter o saldo positivo."

    return {
        "daily_average_expense": round(daily_expense, 2),
        "daily_average_income": round(daily_income, 2),
        "projected_expense_30d": projected_expense,
        "projected_income_30d": projected_income,
        "projected_balance_30d": projected_balance,
        "savings_rate": savings_rate,
        "status": status,
        "message": message,
    }


def classify_bill(due_date: date, is_paid: bool, today: date) -> tuple[str, int, str]:
    """Retorna (status, dias até o vencimento, rótulo). Dias negativos indicam atraso."""
    days_diff = (due_date - today).days
    if is_paid:
        return "paid", days_diff, "Liquidada"
    if days_diff < 0:
        return "overdue", days_diff, f"Atrasada há {abs(days_diff)} dia(s)"
    if days_diff == 0:
        return "today", 0, "Vence hoje!"
    return "upcoming", days_diff, f"Vence em {days_diff} dia(s)"


def build_timeline(
    opening_balance: float,
    daily_totals: dict[date, tuple[float, float]],
    start: date,
    end: date,
) -> list[dict]:
    """Série diária contínua (dias sem movimento repetem o saldo) com saldo acumulado."""
    points: list[dict] = []
    balance = opening_balance
    current = start
    while current <= end:
        income, expense = daily_totals.get(current, (0.0, 0.0))
        net = income - expense
        balance += net
        points.append(
            {
                "date": current,
                "income": round(income, 2),
                "expense": round(expense, 2),
                "daily_net": round(net, 2),
                "cumulative_balance": round(balance, 2),
            }
        )
        current += timedelta(days=1)
    return points


def resolve_client_today(client_today: date | None, server_today: date) -> date:
    """Usa a data local enviada pelo cliente (fuso horário), limitada a ±1 dia do relógio do servidor."""
    if client_today and abs((client_today - server_today).days) <= 1:
        return client_today
    return server_today
