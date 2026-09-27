"""Сериализация моделей FinanceTracker в JSON-файлы."""

import json
from pathlib import Path
from typing import Any

from models import Category, Transaction


def _read_json(filepath: str | Path) -> Any:
    """Прочитать JSON или вернуть пустой список при ошибке файла.

    Args:
        filepath: Путь к JSON-файлу.

    Returns:
        Десериализованные данные или пустой список.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as data_file:
            return json.load(data_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json(filepath: str | Path, data: Any) -> None:
    """Записать JSON, создав родительский каталог при необходимости.

    Args:
        filepath: Путь к JSON-файлу.
        data: JSON-сериализуемые данные.

    Returns:
        Ничего не возвращает.
    """
    destination = Path(filepath)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as data_file:
        json.dump(data, data_file, ensure_ascii=False, indent=4)


def load_categories(filepath: str | Path) -> list[Category]:
    """Загрузить категории из JSON-словаря или списка объектов.

    Args:
        filepath: Путь к файлу категорий.

    Returns:
        Список созданных объектов Category.
    """
    raw_data = _read_json(filepath)
    categories: list[Category] = []

    if isinstance(raw_data, dict):
        for name, limit in raw_data.items():
            category_limit = float(limit) if limit is not None else None
            categories.append(Category(str(name), category_limit))
    elif isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict) and "name" in item:
                categories.append(Category.from_dict(item))

    return categories


def save_categories(
    filepath: str | Path,
    categories: list[Category],
) -> None:
    """Сохранить категории как отображение названий на лимиты.

    Args:
        filepath: Путь к файлу категорий.
        categories: Список объектов Category.

    Returns:
        Ничего не возвращает.
    """
    category_data = {
        category.name: category.limit
        for category in categories
    }
    _write_json(filepath, category_data)


def load_transactions(
    filepath: str | Path,
    categories: list[Category],
) -> list[Transaction]:
    """Загрузить транзакции и связать их с объектами категорий.

    Args:
        filepath: Путь к файлу транзакций.
        categories: Список категорий для разрешения ссылок.

    Returns:
        Список объектов Transaction.
    """
    raw_data = _read_json(filepath)
    if not isinstance(raw_data, list):
        return []

    return [
        Transaction.from_dict(item, categories)
        for item in raw_data
        if isinstance(item, dict)
        and {"id", "amount", "category", "date"}.issubset(item)
    ]


def save_transactions(
    filepath: str | Path,
    transactions: list[Transaction],
) -> None:
    """Сохранить транзакции с названиями категорий вместо объектов.

    Args:
        filepath: Путь к файлу транзакций.
        transactions: Список объектов Transaction.

    Returns:
        Ничего не возвращает.
    """
    _write_json(
        filepath,
        [transaction.to_dict() for transaction in transactions],
    )
