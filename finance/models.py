from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TransactionQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(is_cancelled=True)

    def owned_by(self, user):
        return self.filter(category__owner=user)

    def search(self, query: str):
        return self.filter(
            models.Q(description__icontains=query)
            | models.Q(category__name__icontains=query)
        )


class Category(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE)
    name = models.CharField("название", max_length=80)
    slug = models.SlugField(
        "идентификатор в URL", max_length=100, blank=True,
        allow_unicode=True,
        help_text="Создаётся автоматически из названия.",
    )
    limit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "категория"
        verbose_name_plural = "категории"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_owner_category",
            ),
            models.CheckConstraint(
                condition=models.Q(limit__gte=0) | models.Q(limit=None),
                name="nonnegative_limit",
            ),
            models.UniqueConstraint(
                fields=["owner", "slug"], name="unique_owner_category_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "category"
            candidate = base
            suffix = 2
            while Category.objects.filter(
                owner=self.owner, slug=candidate,
            ).exclude(pk=self.pk).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("finance:category-detail-page", args=[self.slug])


class Transaction(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions",
    )
    amount = models.DecimalField(
        "сумма",
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    type = models.CharField(
        "тип",
        max_length=7, choices=[("income", "Доход"), ("expense", "Расход")],
    )
    date = models.DateField("дата")
    description = models.CharField("описание", max_length=300, blank=True)
    is_cancelled = models.BooleanField("отменена", default=False)
    signed_amount = models.GeneratedField(
        expression=models.Case(
            models.When(type="expense", then=-models.F("amount")),
            default=models.F("amount"),
        ),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
        verbose_name="сумма со знаком",
    )

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "операция"
        verbose_name_plural = "операции"
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

    def get_absolute_url(self) -> str:
        return reverse("finance:transaction-edit", args=[self.pk])


class LedgerState(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True,
    )
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = "состояние финансов"
        verbose_name_plural = "состояния финансов"

    def __str__(self) -> str:
        return f"{self.owner}: версия {self.revision}"
