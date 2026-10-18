import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from finance.forms import CategoryForm, TransactionForm
from finance.models import Category, Transaction
from finance.services import touch_ledger


class Command(BaseCommand):
    help = "Импортировать JSON старой версии в пустой аккаунт"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--directory", type=Path, default=Path("data"))

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
            source = options["directory"]
            with (source / "categories.json").open(encoding="utf-8") as stream:
                categories = json.load(stream)
            transactions_file = source / "transactions.json"
            with transactions_file.open(encoding="utf-8") as stream:
                items = json.load(stream)
        except (User.DoesNotExist, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        if Category.objects.filter(owner=user).exists():
            raise CommandError("Импорт разрешен только в пустой аккаунт")
        if not isinstance(categories, dict) or not isinstance(items, list):
            raise CommandError("Ожидаются словарь категорий и список операций")
        mapping = {}
        for name, limit in categories.items():
            form = CategoryForm({"name": name, "limit": limit})
            if not form.is_valid():
                raise CommandError(
                    f"Категория {name}: {form.errors.as_text()}")
            mapping[name] = Category.objects.create(
                owner=user, **form.cleaned_data,
            )
        for item in items:
            if not isinstance(item, dict):
                raise CommandError("Некорректная запись операции")
            name = item.get("category")
            if not isinstance(name, str) or name not in mapping:
                raise CommandError("Категория операции отсутствует в файле")
            form = TransactionForm(
                {**item, "category": mapping[name].pk}, user=user,
            )
            cancelled = item.get("is_cancelled", False)
            if not form.is_valid() or not isinstance(cancelled, bool):
                raise CommandError(f"Некорректная операция: {form.errors}")
            Transaction.objects.create(
                **form.cleaned_data, is_cancelled=cancelled,
            )
        touch_ledger(user)
        self.stdout.write(self.style.SUCCESS(
            f"Импортировано: {len(mapping)} категорий, {len(items)} операций",
        ))
