from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    limit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_owner_category",
            ),
            models.CheckConstraint(
                condition=models.Q(limit__gte=0) | models.Q(limit=None),
                name="nonnegative_limit",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Transaction(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    type = models.CharField(
        max_length=7, choices=[("income", "Доход"), ("expense", "Расход")],
    )
    date = models.DateField()
    description = models.CharField(max_length=300, blank=True)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["category", "date", "is_cancelled"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="positive_amount",
            ),
            models.CheckConstraint(
                condition=models.Q(type__in=["income", "expense"]),
                name="valid_transaction_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.date}: {self.amount} ({self.category})"


class LedgerState(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True,
    )
    revision = models.PositiveBigIntegerField(default=0)
