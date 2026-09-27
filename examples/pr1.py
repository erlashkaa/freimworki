"""ПР1: один сценарий проверки покупки."""

from datetime import date


def get_transaction_status(is_allowed: bool) -> str:
    """Вернуть статус планируемой покупки."""
    return "Покупка разрешена" if is_allowed else "Лимит превышен"


def main() -> None:
    """Проверить единичный расход с простыми типами данных."""
    category = "Продукты"
    amount = 1200.0
    limit = 15000.0
    purchase_date = date.today()
    is_allowed = amount <= limit
    print(category, purchase_date, get_transaction_status(is_allowed))


if __name__ == "__main__":
    main()
