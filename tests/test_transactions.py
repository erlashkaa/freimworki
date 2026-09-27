"""Тесты объектных моделей и бизнес-логики транзакций."""

from datetime import date

from models import Category, Transaction
from models.categories import add_category, find_category
from models.transactions import (
    add_transaction,
    calculate_net_balance,
    check_expense_limit,
    filter_transactions_by_category,
    sort_transactions_by_amount,
)


def test_category_creation_string_and_dict_conversion() -> None:
    """Категория сохраняет поля и сериализуется в словарь."""
    category = Category("Продукты", 15000.0)

    assert category.name == "Продукты"
    assert category.limit == 15000.0
    assert str(category) == "Продукты (лимит: 15000.00)"
    assert Category.from_dict(category.to_dict()).name == category.name


def test_category_collection_adds_and_finds_objects() -> None:
    """Функции коллекции работают с экземплярами Category."""
    categories: list[Category] = []

    category = add_category(categories, "Транспорт", 5000.0)

    assert find_category(categories, "Транспорт") is category
    assert categories == [category]


def test_transaction_keeps_category_reference_and_formats_text() -> None:
    """Транзакция хранит ссылку на категорию и выводится читаемо."""
    category = Category("Продукты", 15000.0)
    transaction = Transaction(
        1,
        1200.0,
        category,
        "2026-09-27",
        "Покупки",
        "expense",
    )

    assert transaction.category is category
    assert transaction.to_dict()["category"] == "Продукты"
    assert "Продукты" in str(transaction)
    assert "1200.00" in str(transaction)


def test_calculate_net_balance_uses_transaction_objects() -> None:
    """Доходы увеличивают, а расходы уменьшают начальный баланс."""
    category = Category("Зарплата")
    transactions = [
        Transaction(1, 500.0, category, "2026-09-01", "", "income"),
        Transaction(2, 125.0, category, "2026-09-02"),
    ]

    assert calculate_net_balance(transactions, 1000.0) == 1375.0


def test_limit_filter_and_sort_use_object_attributes() -> None:
    """Проверка лимита, фильтр и сортировка работают с моделями."""
    category = Category("Продукты")
    current_month = date.today().strftime("%Y-%m")
    transactions = [
        Transaction(
            1,
            400.0,
            category,
            f"{current_month}-01",
        ),
        Transaction(
            2,
            900.0,
            Category("Транспорт"),
            f"{current_month}-02",
        ),
    ]

    assert check_expense_limit(transactions, "Продукты", 1000.0, 600.0)
    assert not check_expense_limit(transactions, "Продукты", 999.0, 600.0)
    assert list(filter_transactions_by_category(transactions, "Продукты")) == [
        transactions[0]
    ]
    assert sort_transactions_by_amount(transactions)[0] is transactions[1]


def test_add_transaction_appends_existing_transaction() -> None:
    """Функция добавления помещает объект в список и возвращает его."""
    transactions: list[Transaction] = []
    transaction = Transaction(
        1,
        2500.0,
        Category("Зарплата"),
        "2026-09-27",
        transaction_type="income",
    )

    assert add_transaction(transactions, transaction) is transaction
    assert transactions == [transaction]
