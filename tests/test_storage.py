"""Тесты JSON-сериализации моделей FinanceTracker."""

import json
from pathlib import Path

from models import Category, Transaction
from storage import (
    load_categories,
    load_transactions,
    save_categories,
    save_transactions,
)


def test_save_and_load_categories(tmp_path: Path) -> None:
    """Список категорий сохраняется и загружается как объекты."""
    filepath = tmp_path / "categories.json"
    categories = [Category("Продукты", 15000.0), Category("Зарплата")]

    save_categories(filepath, categories)
    loaded_categories = load_categories(filepath)

    assert [category.name for category in loaded_categories] == [
        "Продукты",
        "Зарплата",
    ]
    assert loaded_categories[0].limit == 15000.0
    assert loaded_categories[1].limit is None


def test_save_and_load_transactions_preserves_category_reference(
    tmp_path: Path,
) -> None:
    """JSON-загрузка связывает операцию с общим объектом категории."""
    filepath = tmp_path / "transactions.json"
    category = Category("Продукты", 15000.0)
    categories = [category]
    transactions = [
        Transaction(1, 1200.0, category, "2026-09-27", "Покупки")
    ]

    save_transactions(filepath, transactions)
    loaded_transactions = load_transactions(filepath, categories)

    assert loaded_transactions[0].category is category
    assert loaded_transactions[0].description == "Покупки"
    assert loaded_transactions[0].amount == 1200.0


def test_load_missing_or_invalid_files_returns_empty_lists(
    tmp_path: Path,
) -> None:
    """Отсутствующие и повреждённые файлы безопасно дают пустые коллекции."""
    missing_categories = load_categories(tmp_path / "missing.json")
    missing_transactions = load_transactions(
        tmp_path / "missing_transactions.json",
        [],
    )
    invalid_filepath = tmp_path / "invalid.json"
    invalid_filepath.write_text("{invalid", encoding="utf-8")

    assert missing_categories == []
    assert missing_transactions == []
    assert load_categories(invalid_filepath) == []


def test_categories_json_mapping_is_supported(tmp_path: Path) -> None:
    """Старый формат JSON-словаря категорий продолжает загружаться."""
    filepath = tmp_path / "categories.json"
    filepath.write_text(
        json.dumps({"Транспорт": 5000.0}, ensure_ascii=False),
        encoding="utf-8",
    )

    loaded_categories = load_categories(filepath)

    assert loaded_categories[0].name == "Транспорт"
    assert loaded_categories[0].limit == 5000.0
