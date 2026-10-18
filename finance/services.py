from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.db.models import F, Q, Sum

from .models import Category, LedgerState, Transaction


def touch_ledger(user) -> None:
    LedgerState.objects.get_or_create(owner=user)
    LedgerState.objects.filter(owner=user).update(revision=F("revision") + 1)


def money(value) -> str:
    return f"{value or Decimal('0'):.2f}"


def summary(user, month: date) -> dict:
    revision = LedgerState.objects.filter(owner=user).values_list(
        "revision", flat=True,
    ).first() or 0
    key = f"summary:{user.pk}:{revision}:{month:%Y-%m}"
    result = cache.get(key)
    if result is not None:
        return result
    active = Transaction.objects.filter(
        category__owner=user, is_cancelled=False,
    )
    totals = active.aggregate(
        income=Sum("amount", filter=Q(type="income")),
        expense=Sum("amount", filter=Q(type="expense")),
    )
    monthly = active.filter(date__year=month.year, date__month=month.month)
    spent = dict(monthly.filter(type="expense").values("category_id").annotate(
        total=Sum("amount"),
    ).values_list("category_id", "total"))
    month_totals = monthly.aggregate(
        income=Sum("amount", filter=Q(type="income")),
        expense=Sum("amount", filter=Q(type="expense")),
    )
    result = {
        "balance": money((totals["income"] or 0) - (totals["expense"] or 0)),
        "month": month.strftime("%Y-%m"),
        "income": money(month_totals["income"]),
        "expense": money(month_totals["expense"]),
        "categories": [{
            "id": c.id, "name": c.name,
            "limit": None if c.limit is None else money(c.limit),
            "spent": money(spent.get(c.id)),
            "remaining": None if c.limit is None else money(
                c.limit - spent.get(c.id, Decimal("0")),
            ),
        } for c in Category.objects.filter(owner=user)],
    }
    cache.set(key, result, 60)
    return result
