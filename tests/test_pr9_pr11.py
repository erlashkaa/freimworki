from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from finance.admin import cancel_transactions
from finance.forms import TransactionFilterForm, TransactionModelForm
from finance.models import Category, LedgerState, Transaction
from finance.selectors import category_statistics, transaction_queryset


@pytest.fixture
def owner(db):
    return User.objects.create_user("owner", password="Strong-pass-937!")


@pytest.fixture
def category(owner):
    return Category.objects.create(owner=owner, name="Продукты", limit=5000)


@pytest.fixture
def web_client(owner):
    client = Client()
    client.force_login(owner)
    return client


@pytest.mark.django_db
def test_models_slug_reverse_relations_and_generated_field(owner):
    first = Category.objects.create(owner=owner, name="Еда!")
    second = Category.objects.create(owner=owner, name="Еда?")
    item = Transaction.objects.create(
        category=first, amount="125.50", type="expense",
        date=timezone.localdate(), description="Обед",
    )
    item.refresh_from_db()

    assert first.slug == "еда"
    assert second.slug == "еда-2"
    assert first.transactions.get() == item
    assert item.signed_amount == Decimal("-125.50")
    assert first.get_absolute_url().startswith("/categories/")


@pytest.mark.django_db
def test_queryset_filters_search_exclude_annotate_and_values(owner, category):
    active = Transaction.objects.create(
        category=category, amount=100, type="expense",
        date=timezone.localdate(), description="Супермаркет",
    )
    Transaction.objects.create(
        category=category, amount=50, type="income",
        date=timezone.localdate(), description="Возврат", is_cancelled=True,
    )
    form = TransactionFilterForm({"query": "Суп"}, user=owner)

    assert form.is_valid()
    assert list(transaction_queryset(owner, form.cleaned_data)) == [active]
    stats = list(category_statistics(owner))
    assert stats[0]["operation_count"] == 2
    assert stats[0]["expense_total"] == Decimal("100")
    assert Transaction.objects.owned_by(owner).active().count() == 1


@pytest.mark.django_db
def test_api_search_and_paginator(web_client, category):
    Transaction.objects.bulk_create([
        Transaction(
            category=category, amount=index + 1, type="expense",
            date=timezone.localdate(), description=f"Покупка {index}",
        )
        for index in range(21)
    ])
    response = web_client.get("/api/transactions/?query=Покупка&page=2")

    assert response.status_code == 200
    assert response.json()["count"] == 21
    assert len(response.json()["results"]) == 1
    response = web_client.get("/api/transactions/?page=99")
    assert response.status_code == 400


@pytest.mark.django_db
def test_model_form_create_edit_cancel_and_ownership(
    web_client, owner, category,
):
    today = timezone.localdate().isoformat()
    create = web_client.post(reverse("finance:transaction-create"), {
        "type": "expense", "amount": "450.25", "category": category.pk,
        "date": today, "description": "Учебники",
    })
    item = Transaction.objects.get()

    assert create.status_code == 302
    edit_url = reverse("finance:transaction-edit", args=[item.pk])
    edit = web_client.post(edit_url, {
        "type": "expense", "amount": "400.00", "category": category.pk,
        "date": today, "description": "Книги",
    })
    assert edit.status_code == 302
    item.refresh_from_db()
    assert item.amount == Decimal("400.00")
    cancel = web_client.post(
        reverse("finance:transaction-cancel", args=[item.pk]),
    )
    assert cancel.status_code == 302
    item.refresh_from_db()
    assert item.is_cancelled

    other = User.objects.create_user("other")
    foreign = Category.objects.create(owner=other, name="Чужая")
    form = TransactionModelForm({
        "type": "expense", "amount": 1, "category": foreign.pk,
        "date": today,
    }, user=owner)
    assert not form.is_valid()


@pytest.mark.django_db
def test_form_rejects_future_date_and_pages_require_login(owner, category):
    tomorrow = timezone.localdate() + timedelta(days=1)
    form = TransactionModelForm({
        "type": "income", "amount": 100, "category": category.pk,
        "date": tomorrow.isoformat(),
    }, user=owner)
    assert not form.is_valid()
    assert "будущем" in form.errors["date"][0]
    assert Client().get(reverse("finance:transaction-list")).status_code == 302


@pytest.mark.django_db
def test_admin_lists_finance_models(owner, category):
    owner.is_staff = True
    owner.is_superuser = True
    owner.save(update_fields=["is_staff", "is_superuser"])
    client = Client()
    client.force_login(owner)

    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/finance/category/").status_code == 200
    assert client.get("/admin/finance/transaction/").status_code == 200
    assert client.get(category.get_absolute_url()).status_code == 200


@pytest.mark.django_db
def test_admin_cancel_action_invalidates_summary(owner, category):
    item = Transaction.objects.create(
        category=category, amount=10, type="expense",
        date=timezone.localdate(),
    )
    cancel_transactions(
        None, None, Transaction.objects.filter(pk=item.pk),
    )

    item.refresh_from_db()
    assert item.is_cancelled
    assert LedgerState.objects.get(owner=owner).revision == 1


@pytest.mark.django_db
def test_html_cancel_requires_csrf(owner, category):
    item = Transaction.objects.create(
        category=category, amount=1, type="expense",
        date=timezone.localdate(),
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)
    response = client.post(
        reverse("finance:transaction-cancel", args=[item.pk]),
    )
    assert response.status_code == 403
