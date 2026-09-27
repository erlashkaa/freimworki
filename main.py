"""Интерактивное консольное приложение FinanceTracker."""

from pathlib import Path

from models import Category, Transaction
from models.categories import (
    add_category,
    find_category,
    get_categories,
    get_limit_for_category,
)
from models.transactions import (
    add_transaction,
    calculate_net_balance,
    check_expense_limit,
    filter_transactions_by_category,
    get_transaction_status,
    sort_transactions_by_amount,
)
from storage import (
    load_categories,
    load_transactions,
    save_categories,
    save_transactions,
)
from utils import input_date, input_float

INITIAL_BALANCE = 0.0
DATA_DIRECTORY = Path(__file__).parent / "data"
TRANSACTIONS_FILE = DATA_DIRECTORY / "transactions.json"
CATEGORIES_FILE = DATA_DIRECTORY / "categories.json"


def _display_summary(
    categories: list[Category],
    transactions: list[Transaction],
) -> None:
    """Напечатать текущий баланс и расходы по категориям.

    Args:
        categories: Список категорий с лимитами.
        transactions: Список финансовых операций.

    Returns:
        Ничего не возвращает.
    """
    balance = calculate_net_balance(transactions, INITIAL_BALANCE)
    print(f"Текущий баланс: {balance:.2f}")
    print("Сводка расходов по категориям:")
    for category in get_categories(categories):
        category_expenses = sum(
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
            and transaction.category.name == category.name
        )
        limit_text = (
            f"{category.limit:.2f}"
            if category.limit is not None
            else "не задан"
        )
        print(
            f"- {category.name}: {category_expenses:.2f} / "
            f"лимит {limit_text}"
        )
    if not categories:
        print("Категории пока не добавлены.")


def _create_transaction(
    categories: list[Category],
    transactions: list[Transaction],
) -> None:
    """Запросить данные операции и добавить объект транзакции.

    Args:
        categories: Список категорий для поиска или добавления.
        transactions: Список операций для пополнения.

    Returns:
        Ничего не возвращает.
    """
    transaction_type = input("Тип операции (income/expense): ").strip().lower()
    while transaction_type not in ("income", "expense"):
        print("Введите income или expense.")
        transaction_type = input(
            "Тип операции (income/expense): "
        ).strip().lower()

    category_name = input("Категория: ").strip()
    while not category_name:
        print("Название категории не должно быть пустым.")
        category_name = input("Категория: ").strip()

    category = find_category(categories, category_name)
    if category is None:
        category = add_category(categories, category_name)

    amount = input_float("Сумма: ")
    while amount <= 0:
        print("Сумма должна быть больше нуля.")
        amount = input_float("Сумма: ")
    transaction_date = input_date("Дата (YYYY-MM-DD): ")
    description = input("Описание (необязательно): ").strip()

    next_id = max((transaction.id for transaction in transactions), default=0)
    transaction = Transaction(
        transaction_id=next_id + 1,
        amount=amount,
        category=category,
        date=transaction_date,
        description=description,
        transaction_type=transaction_type,
    )
    add_transaction(transactions, transaction)
    print(f"Добавлена операция: {transaction}")


def _check_category_limit(
    categories: list[Category],
    transactions: list[Transaction],
) -> None:
    """Проверить планируемую покупку по лимиту выбранной категории.

    Args:
        categories: Список категорий и лимитов.
        transactions: Список операций текущего периода.

    Returns:
        Ничего не возвращает.
    """
    category_name = input("Категория покупки: ").strip()
    limit = get_limit_for_category(categories, category_name)
    if limit is None:
        print("Для этой категории лимит не задан.")
        return

    new_amount = input_float("Сумма покупки: ")
    is_allowed = check_expense_limit(
        transactions,
        category_name,
        limit,
        new_amount,
    )
    print(get_transaction_status(is_allowed))


def _display_history(transactions: list[Transaction]) -> None:
    """Показать историю с фильтрацией или сортировкой.

    Args:
        transactions: Список операций для отображения.

    Returns:
        Ничего не возвращает.
    """
    print("1. Фильтровать по категории")
    print("2. Сортировать по сумме")
    history_choice = input("Выберите способ просмотра: ").strip()
    if history_choice == "1":
        category_name = input("Категория: ").strip()
        has_transactions = False
        for transaction in filter_transactions_by_category(
            transactions,
            category_name,
        ):
            print(transaction)
            has_transactions = True
        if not has_transactions:
            print("Операций в этой категории нет.")
    elif history_choice == "2":
        for transaction in sort_transactions_by_amount(transactions):
            print(transaction)
    else:
        print("Неизвестный способ просмотра истории.")


def main() -> None:
    """Загрузить данные, обработать меню и сохранить изменения при выходе."""
    categories = load_categories(CATEGORIES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE, categories)

    while True:
        print("\n=== FinanceTracker ===")
        print("1. Показать баланс и сводку по категориям")
        print("2. Добавить транзакцию")
        print("3. Проверить лимит категории перед покупкой")
        print("4. Показать историю транзакций")
        print("5. Сохранить изменения и выйти")
        menu_choice = input("Выберите пункт меню: ").strip()

        if menu_choice == "1":
            _display_summary(categories, transactions)
        elif menu_choice == "2":
            _create_transaction(categories, transactions)
        elif menu_choice == "3":
            _check_category_limit(categories, transactions)
        elif menu_choice == "4":
            _display_history(transactions)
        elif menu_choice == "5":
            save_transactions(TRANSACTIONS_FILE, transactions)
            save_categories(CATEGORIES_FILE, categories)
            print("Данные сохранены. До встречи!")
            break
        else:
            print("Выберите пункт меню от 1 до 5.")


if __name__ == "__main__":
    main()
