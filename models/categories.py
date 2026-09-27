"""Модель категории и функции работы со списком категорий."""

from math import isfinite
from typing import Any


class Category:
    """Категория расходов с необязательным лимитом."""

    def __init__(self, name: str, limit: float | None = None) -> None:
        """Инициализировать категорию.

        Args:
            name: Название категории.
            limit: Лимит расходов или None, если лимит не задан.
        """
        self.validate_limit(limit)
        if not name.strip():
            raise ValueError("Название категории не должно быть пустым")
        self.name = name
        self.limit = limit

    @staticmethod
    def validate_limit(limit: float | None) -> None:
        """Проверить неотрицательный конечный лимит."""
        if limit is not None and (not isfinite(limit) or limit < 0):
            raise ValueError("Лимит должен быть конечным и неотрицательным")

    def allows(self, spent: float, amount: float) -> bool:
        """Проверить покупку с учётом уже потраченной суммы."""
        return self.limit is None or spent + amount <= self.limit

    def __str__(self) -> str:
        """Вернуть название категории и её лимит, если он задан."""
        if self.limit is None:
            return self.name
        return f"{self.name} (лимит: {self.limit:.2f})"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        """Создать категорию из словаря JSON.

        Args:
            data: Словарь с ключами name и limit.

        Returns:
            Новый объект категории.
        """
        raw_limit = data.get("limit")
        limit = float(raw_limit) if raw_limit is not None else None
        return cls(name=str(data["name"]), limit=limit)

    def to_dict(self) -> dict[str, str | float | None]:
        """Преобразовать категорию в словарь для JSON-сериализации.

        Returns:
            Словарь с названием категории и лимитом.
        """
        return {"name": self.name, "limit": self.limit}


def find_category(
    categories: list[Category],
    name: str,
) -> Category | None:
    """Найти категорию по названию.

    Args:
        categories: Список объектов категорий.
        name: Искомое название.

    Returns:
        Найденный объект категории или None.
    """
    for category in categories:
        if category.name == name:
            return category
    return None


def add_category(
    categories: list[Category],
    name: str,
    limit: float | None = None,
) -> Category:
    """Добавить категорию или обновить лимит существующей.

    Args:
        categories: Список категорий для изменения.
        name: Название категории.
        limit: Лимит расходов или None.

    Returns:
        Добавленный или обновлённый объект категории.
    """
    Category.validate_limit(limit)
    existing_category = find_category(categories, name)
    if existing_category is not None:
        existing_category.limit = limit
        return existing_category

    new_category = Category(name, limit)
    categories.append(new_category)
    return new_category


def get_categories(categories: list[Category]) -> list[Category]:
    """Вернуть список категорий.

    Args:
        categories: Список категорий.

    Returns:
        Переданный список объектов категорий.
    """
    return categories


def get_limit_for_category(
    categories: list[Category],
    name: str,
) -> float | None:
    """Получить лимит категории или None, если категория не найдена.

    Args:
        categories: Список категорий.
        name: Название категории.

    Returns:
        Лимит категории либо None.
    """
    category = find_category(categories, name)
    return category.limit if category is not None else None
