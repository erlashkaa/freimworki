"""Модель транзакции и функции работы со списком операций."""

from datetime import date
from math import isfinite
from typing import Any, Iterator

from models.categories import Category, find_category


class Transaction:
    """Финансовая операция, связанная с объектом категории."""

    def __init__(
        self,
        transaction_id: int,
        amount: float,
        category: Category,
        date: str,
        description: str = "",
        transaction_type: str = "expense",
    ) -> None:
        """Инициализировать транзакцию.

        Args:
            transaction_id: Уникальный идентификатор операции.
            amount: Сумма операции.
            category: Объект категории этой операции.
            date: Дата операции в формате YYYY-MM-DD.
            description: Необязательное описание.
            transaction_type: Тип операции income или expense.
        """
        if not isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть конечной и положительной")
        if transaction_type not in ("income", "expense"):
            raise ValueError("Неизвестный тип операции")
        self.is_cancelled = False
        self.id = transaction_id
        self.amount = amount
        self.category = category
        self.date = date
        self.description = description
        self.type = transaction_type

    def cancel(self) -> None:
        """Отменить операцию, сохранив её в истории."""
        self.is_cancelled = True

    def __str__(self) -> str:
        """Вернуть читаемое представление финансовой операции."""
        type_label = "Доход" if self.type == "income" else "Расход"
        status = " [отменена]" if self.is_cancelled else ""
        return (
            f"#{self.id}{status} | {self.date} | {type_label} | "
            f"{self.category.name} | "
            f"{self.amount:.2f} | {self.description}"
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        categories: list[Category],
    ) -> "Transaction":
        """Создать операцию и разрешить название категории в объект.

        Args:
            data: Словарь транзакции из JSON.
            categories: Список категорий, используемый для поиска ссылки.

        Returns:
            Новая транзакция, связанная с объектом категории.
        """
        category_name = str(data["category"])
        category = find_category(categories, category_name)
        if category is None:
            category = Category(category_name)
            categories.append(category)

        transaction = cls(
            transaction_id=int(data["id"]),
            amount=float(data["amount"]),
            category=category,
            date=str(data["date"]),
            description=str(data.get("description", "")),
            transaction_type=str(data.get("type", "expense")),
        )

        transaction.is_cancelled = bool(data.get("is_cancelled", False))
        return transaction

    def to_dict(self) -> dict[str, int | float | str]:
        """Преобразовать транзакцию в JSON-совместимый словарь.

        Returns:
            Словарь транзакции с названием категории вместо объекта.
        """
        return {
            "id": self.id,
            "is_cancelled": self.is_cancelled,
            "type": self.type,
            "category": self.category.name,
            "amount": self.amount,
            "date": self.date,
            "description": self.description,
        }


def calculate_net_balance(
    transactions: list[Transaction],
    initial_balance: float,
) -> float:
    """Рассчитать итоговый баланс по списку транзакций.

    Args:
        transactions: Список доходов и расходов.
        initial_balance: Баланс до учёта операций.

    Returns:
        Баланс после применения каждой транзакции.
    """
    current_balance = initial_balance
    for transaction in transactions:
        if transaction.is_cancelled:
            continue
        if transaction.type == "income":
            current_balance += transaction.amount
        elif transaction.type == "expense":
            current_balance -= transaction.amount
    return current_balance


def check_expense_limit(
    transactions: list[Transaction],
    category: str,
    limit: float,
    new_amount: float,
) -> bool:
    """Проверить покупку по расходам категории за текущий месяц.

    Args:
        transactions: Список ранее зарегистрированных операций.
        category: Название категории покупки.
        limit: Месячный лимит расходов.
        new_amount: Сумма планируемой покупки.

    Returns:
        True, если покупка не превышает лимит, иначе False.
    """
    if not isfinite(new_amount) or new_amount <= 0:
        raise ValueError("Сумма покупки должна быть положительной")
    current_month = date.today().strftime("%Y-%m")
    category_expenses = 0.0
    for transaction in transactions:
        if (
            not transaction.is_cancelled
            and transaction.type == "expense"
            and transaction.category.name == category
            and transaction.date.startswith(current_month)
        ):
            category_expenses += transaction.amount
    return category_expenses + new_amount <= limit


def get_transaction_status(is_allowed: bool) -> str:
    """Вернуть текстовый результат проверки лимита.

    Args:
        is_allowed: Результат проверки возможности покупки.

    Returns:
        Понятное пользователю сообщение о результате.
    """
    if is_allowed:
        return "Покупка укладывается в лимит категории."
    return "Покупка превысит лимит категории."


def add_transaction(
    transactions: list[Transaction],
    transaction: Transaction,
) -> Transaction:
    """Добавить созданную транзакцию в список.

    Args:
        transactions: Список операций для изменения.
        transaction: Объект операции для добавления.

    Returns:
        Добавленный объект транзакции.
    """
    transactions.append(transaction)
    return transaction


def filter_transactions_by_category(
    transactions: list[Transaction],
    category: str,
) -> Iterator[Transaction]:
    """Отобрать транзакции по категории ленивым генератором.

    Args:
        transactions: Список операций для фильтрации.
        category: Название нужной категории.

    Returns:
        Итератор подходящих транзакций.
    """
    return (
        transaction
        for transaction in transactions
        if transaction.category.name == category
    )


def sort_transactions_by_amount(
    transactions: list[Transaction],
    reverse: bool = True,
) -> list[Transaction]:
    """Отсортировать копию транзакций по сумме.

    Args:
        transactions: Список операций.
        reverse: True для порядка от большей суммы к меньшей.

    Returns:
        Новый отсортированный список.
    """
    return sorted(
        transactions,
        key=lambda transaction: transaction.amount,
        reverse=reverse,
    )
