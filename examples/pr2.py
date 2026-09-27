"""ПР2: пример коллекций до перехода на объектную модель."""

from datetime import date


def add_transaction(items: list[dict], amount: float) -> dict:
    """Добавить операцию, представленную словарём."""
    item = {
        "id": max((entry["id"] for entry in items), default=0) + 1,
        "category": "Продукты",
        "amount": amount,
        "date": date.today().isoformat(),
    }
    items.append(item)
    return item


def main() -> None:
    """Показать list, dict, set и tuple на данных операций."""
    transactions: list[dict] = []
    add_transaction(transactions, 1200.0)
    add_transaction(transactions, 500.0)
    categories: set[str] = {item["category"] for item in transactions}
    operation_types: tuple[str, str] = ("income", "expense")
    ordered = sorted(transactions, key=lambda item: item["amount"])
    selected = [item for item in ordered if item["amount"] >= 1000]
    print(categories, operation_types, selected)


if __name__ == "__main__":
    main()
