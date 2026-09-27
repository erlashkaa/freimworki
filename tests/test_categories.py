"""Тесты модели и коллекционных функций категорий."""

from models import Category
from models.categories import (
    add_category,
    find_category,
    get_categories,
    get_limit_for_category,
)


def test_category_without_limit_and_from_dict() -> None:
    """Категория поддерживает незаданный лимит и JSON-словарь."""
    category = Category.from_dict({"name": "Зарплата", "limit": None})

    assert category.name == "Зарплата"
    assert category.limit is None
    assert str(category) == "Зарплата"
    assert category.to_dict() == {"name": "Зарплата", "limit": None}


def test_add_category_updates_existing_entry() -> None:
    """Добавление существующего имени обновляет лимит без дубликата."""
    categories = [Category("Продукты", 10000.0)]

    updated_category = add_category(categories, "Продукты", 15000.0)

    assert len(categories) == 1
    assert categories[0] is updated_category
    assert updated_category.limit == 15000.0


def test_category_collection_accessors() -> None:
    """Поиск и получение списка/лимита используют объекты Category."""
    category = Category("Транспорт", 5000.0)
    categories = [category]

    assert get_categories(categories) is categories
    assert find_category(categories, "Транспорт") is category
    assert get_limit_for_category(categories, "Транспорт") == 5000.0
    assert get_limit_for_category(categories, "Досуг") is None
