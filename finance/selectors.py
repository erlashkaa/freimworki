from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Category, Transaction


def transaction_queryset(user, cleaned_data):
    items = Transaction.objects.owned_by(user).select_related(
        "category", "category__owner",
    )
    if not cleaned_data.get("include_cancelled"):
        items = items.active()
    if cleaned_data.get("query"):
        items = items.search(cleaned_data["query"])
    if cleaned_data.get("category"):
        items = items.filter(category=cleaned_data["category"])
    if cleaned_data.get("type"):
        items = items.filter(type=cleaned_data["type"])
    if cleaned_data.get("month"):
        month = cleaned_data["month"]
        items = items.filter(date__year=month.year, date__month=month.month)
    return items.order_by(cleaned_data.get("ordering") or "-date", "-id")


def category_statistics(user):
    zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
    return Category.objects.filter(owner=user).annotate(
        operation_count=Count("transactions"),
        expense_total=Coalesce(Sum(
            "transactions__amount",
            filter=Q(
                transactions__type="expense",
                transactions__is_cancelled=False,
            ),
        ), zero),
    ).values("id", "name", "slug", "operation_count", "expense_total")
