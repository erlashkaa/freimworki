from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import Client

from finance.models import Category, Transaction
from finance.services import summary


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def web_user(db):
    return User.objects.create_user("erlan", password="Strong-example-937!")


@pytest.fixture
def api_client(web_user):
    client = Client()
    client.force_login(web_user)
    return client


def post(client, path, data):
    return client.post(path, data, content_type="application/json")


def category_for(user):
    return Category.objects.create(owner=user, name="Еда", limit="100.00")


def operation(cat, **updates):
    data = {"category": cat.pk, "amount": "80.00", "type": "expense",
            "date": "2026-10-18", "description": "Покупки"}
    return {**data, **updates}


@pytest.mark.django_db
def test_register_login_logout_and_password_hash():
    client = Client(enforce_csrf_checks=True)
    token = client.get("/api/session/").json()["csrfToken"]
    response = client.post("/api/register/", {
        "username": "newuser", "password1": "Strong-example-937!",
        "password2": "Strong-example-937!",
    }, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 201
    user = User.objects.get(username="newuser")
    assert user.password != "Strong-example-937!"
    assert user.check_password("Strong-example-937!")
    token = response.json()["csrfToken"]
    assert client.post("/api/logout/", {}, content_type="application/json",
                       HTTP_X_CSRFTOKEN=token).status_code == 200
    assert client.get("/api/categories/").status_code == 401
    response = client.post("/api/login/", {
        "username": "newuser", "password": "Strong-example-937!",
    }, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


@pytest.mark.django_db
def test_csrf_required_on_registration_and_writes(web_user):
    client = Client(enforce_csrf_checks=True)
    assert post(client, "/api/register/", {}).status_code == 403
    client.force_login(web_user)
    assert post(client, "/api/categories/", {"name": "Еда"}).status_code == 403
    assert client.get("/api/logout/").status_code == 405


@pytest.mark.django_db
def test_weak_password_and_login_rate_limit():
    client = Client()
    response = post(client, "/api/register/", {
        "username": "person", "password1": "123", "password2": "123",
    })
    assert response.status_code == 400
    assert not User.objects.exists()
    for _ in range(30):
        response = post(client, "/api/login/",
                        {"username": "", "password": ""})
        assert response.status_code == 401
    assert post(client, "/api/login/", {}).status_code == 429


def test_foreign_data_is_inaccessible(api_client, web_user):
    other = User.objects.create_user("other")
    category = category_for(other)
    item = Transaction.objects.create(
        category=category, amount=80, type="expense", date="2026-10-18",
    )
    assert api_client.get("/api/categories/").json()["results"] == []
    assert api_client.get("/api/transactions/").json()["count"] == 0
    assert post(api_client, "/api/transactions/",
                operation(category)).status_code == 400
    response = api_client.patch(f"/api/categories/{category.pk}/", {
        "name": "Changed",
    }, content_type="application/json")
    assert response.status_code == 404
    assert post(api_client,
                f"/api/transactions/{item.pk}/cancel/",
                {}).status_code == 404
    assert api_client.get("/api/summary/").json()["balance"] == "0.00"


def test_money_month_and_cancellation(api_client, web_user):
    category = category_for(web_user)
    post(api_client, "/api/transactions/", operation(
        category, type="income", amount="200.10", date="2026-09-30",
    ))
    created = post(api_client, "/api/transactions/", operation(category))
    assert created.status_code == 201
    path = "/api/summary/?month=2026-10"
    result = api_client.get(path).json()
    assert result["balance"] == "120.10"
    assert result["income"] == "0.00"
    assert result["expense"] == "80.00"
    assert result["categories"][0]["remaining"] == "20.00"
    for _ in range(2):
        assert post(api_client, "/api/transactions/"
                    f"{created.json()['id']}/cancel/", {}).status_code == 200
    result = api_client.get(path).json()
    assert result["balance"] == "200.10"
    assert result["expense"] == "0.00"
    assert Transaction.objects.count() == 2


@pytest.mark.parametrize("field,value", [
    ("amount", "0"), ("amount", "-1"), ("amount", "NaN"),
    ("amount", "Infinity"), ("amount", "1.001"),
    ("amount", "10000000000"), ("date", "2026-02-30"),
    ("type", "transfer"), ("description", "x" * 301),
    ("category", True), ("amount", {"bad": 1}),
])
def test_invalid_operation(api_client, web_user, field, value):
    category = category_for(web_user)
    response = post(api_client, "/api/transactions/", operation(
        category, **{field: value},
    ))
    assert response.status_code == 400
    assert Transaction.objects.count() == 0


def test_categories_duplicates_update_and_invalid_limit(api_client, web_user):
    response = post(api_client, "/api/categories/",
                    {"name": "Еда", "limit": 100})
    assert response.status_code == 201
    pk = response.json()["id"]
    assert post(api_client, "/api/categories/",
                {"name": "Еда"}).status_code == 409
    assert post(api_client, "/api/categories/",
                {"name": ""}).status_code == 400
    assert post(api_client, "/api/categories/", {
        "name": "Другое", "limit": -1,
    }).status_code == 400
    summary(web_user, date(2026, 10, 1))
    response = api_client.patch(f"/api/categories/{pk}/", {
        "limit": "50.00",
    }, content_type="application/json")
    assert response.status_code == 200
    assert summary(web_user, date(2026, 10, 1))[
        "categories"][0]["limit"] == "50.00"


def test_history_filter_sort_pagination(api_client, web_user):
    category = category_for(web_user)
    Transaction.objects.bulk_create([
        Transaction(category=category, amount=i + 1, type="expense",
                    date="2026-10-18") for i in range(25)
    ])
    result = api_client.get("/api/transactions/?ordering=-amount").json()
    assert result["count"] == 25
    assert len(result["results"]) == 20
    assert result["results"][0]["amount"] == "25.00"
    assert len(api_client.get(
        "/api/transactions/?page=2").json()["results"]) == 5
    assert api_client.get(
        "/api/transactions/?month=2026-09").json()["count"] == 0
    assert api_client.get(
        "/api/transactions/?category=9999").json()["count"] == 0
    for query in ("page=0", "page=no", "ordering=password", "month=no"):
        assert api_client.get(f"/api/transactions/?{query}").status_code == 400


def test_summary_cache_and_query_budget(api_client, web_user,
                                        django_assert_num_queries):
    category = category_for(web_user)
    with django_assert_num_queries(5):
        first = summary(web_user, date(2026, 10, 1))
    with django_assert_num_queries(1):
        assert summary(web_user, date(2026, 10, 1)) == first
    post(api_client, "/api/transactions/", operation(category))
    assert summary(web_user, date(2026, 10, 1))["expense"] == "80.00"


def test_database_rejects_negative_amount(web_user):
    category = category_for(web_user)
    with pytest.raises(IntegrityError), transaction.atomic():
        Transaction.objects.create(category=category, amount=Decimal("-1"),
                                   type="expense", date="2026-10-18")


def test_summary_cache_is_separate_for_each_user(web_user):
    other = User.objects.create_user("second")
    category = category_for(web_user)
    Transaction.objects.create(category=category, amount=50,
                               type="income", date="2026-10-18")
    assert summary(web_user, date(2026, 10, 1))["balance"] == "50.00"
    assert summary(other, date(2026, 10, 1))["balance"] == "0.00"


def test_bad_json_and_security_headers(api_client):
    assert api_client.post(
        "/api/categories/",
        "{",
        content_type="application/json").status_code == 400
    assert post(api_client, "/api/categories/", []).status_code == 400
    assert api_client.post(
        "/api/categories/", {"name": "Еда"}).status_code == 415
    response = api_client.get("/")
    assert response.status_code == 200
    assert "script-src 'self'" in response["Content-Security-Policy"]
    assert response["X-Frame-Options"] == "DENY"
    assert response["Cache-Control"] == "no-store"
    assert api_client.get("/api/categories/")["Cache-Control"] == "no-store"
