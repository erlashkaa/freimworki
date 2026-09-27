"""Функции безопасного ввода данных из консоли."""

from datetime import datetime
from math import isfinite


def input_float(prompt: str) -> float:
    """Запрашивать число с плавающей точкой до корректного ввода.

    Args:
        prompt: Текст приглашения для пользователя.

    Returns:
        Введённое пользователем число.
    """
    while True:
        user_input = input(prompt).strip().replace(",", ".")
        try:
            value = float(user_input)
            if not isfinite(value):
                raise ValueError("Введите конечное число")
            return value
        except ValueError:
            print("Некорректное число. Попробуйте ещё раз.")


def input_date(prompt: str) -> str:
    """Запрашивать дату до корректного формата и календарного значения.

    Args:
        prompt: Текст приглашения для пользователя.

    Returns:
        Дата в формате YYYY-MM-DD.
    """
    while True:
        user_input = input(prompt).strip()
        try:
            parsed_date = datetime.strptime(user_input, "%Y-%m-%d")
            return parsed_date.date().isoformat()
        except ValueError:
            print("Некорректная дата. Используйте формат YYYY-MM-DD.")


def input_int(prompt: str) -> int:
    """Повторять ввод целого числа при ValueError."""
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Введите целое число.")
