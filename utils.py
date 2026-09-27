"""Функции безопасного ввода данных из консоли."""

from datetime import datetime


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
            return float(user_input)
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
