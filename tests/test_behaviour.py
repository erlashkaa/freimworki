"""Проверка отмены операций, валидации и безопасного ввода."""

from datetime import date

import pytest

from models import Category, Transaction
from models.transactions import calculate_net_balance, check_expense_limit
from storage import load_transactions, save_transactions
from utils import input_date, input_float, input_int


def test_cancel_restores_balance_and_limit(tmp_path) -> None:
    category = Category("Еда", 100)
    item = Transaction(1, 80, category, date.today().isoformat())
    assert not check_expense_limit([item], "Еда", 100, 30)
    item.cancel()
    item.cancel()
    assert calculate_net_balance([item], 100) == 100
    assert check_expense_limit([item], "Еда", 100, 30)
    path = tmp_path / "transactions.json"
    save_transactions(path, [item])
    restored = load_transactions(path, [category])[0]
    assert restored.is_cancelled
    assert restored.category is category


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_limits_and_amounts(value) -> None:
    with pytest.raises(ValueError):
        Category("Еда", value)
    with pytest.raises(ValueError):
        Transaction(1, value, Category("Еда"), "2026-09-27")


def test_category_behaviour() -> None:
    assert Category("Еда", 100).allows(80, 20)
    assert not Category("Еда", 100).allows(80, 21)


@pytest.mark.parametrize(
    "reader,answers,expected",
    [
        (input_int, ["abc", "2.5", "6"], 6),
        (input_float, ["nan", "inf", "abc", "2,5"], 2.5),
        (input_date, ["2026-02-30", "2026-02-28"], "2026-02-28"),
    ],
)
def test_safe_input(monkeypatch, reader, answers, expected) -> None:
    values = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))
    assert reader("Значение: ") == expected
