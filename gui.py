"""Минимальный оконный интерфейс FinanceTracker на Tkinter."""

from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from models import Category, Transaction
from models.categories import find_category
from models.transactions import calculate_net_balance
from storage import (
    load_categories, load_transactions, save_categories, save_transactions,
)


class FinanceApp:
    """Форма добавления операций и таблица истории."""

    def __init__(self, root: tk.Tk, data_dir: Path) -> None:
        self.root = root
        self.data_dir = data_dir
        self.categories = load_categories(data_dir / "categories.json")
        self.transactions = load_transactions(
            data_dir / "transactions.json", self.categories,
        )
        root.title("FinanceTracker — личные финансы")
        root.geometry("960x600")
        root.minsize(800, 500)
        self.dirty = False
        self.editing_index: int | None = None
        root.protocol("WM_DELETE_WINDOW", self.close)
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill="both", expand=True)
        self.balance = tk.StringVar()
        ttk.Label(panel, text="Личные финансы", font=("Segoe UI", 20)).pack(
            anchor="w",
        )
        ttk.Label(panel, textvariable=self.balance,
                  font=("Segoe UI", 14)).pack(anchor="w", pady=(8, 16))
        form = ttk.LabelFrame(panel, text="Новая операция", padding=12)
        form.pack(fill="x")
        self.kind = tk.StringVar(value="Расход")
        self.category = tk.StringVar()
        self.amount = tk.StringVar()
        self.day = tk.StringVar(value=date.today().isoformat())
        self.description = tk.StringVar()
        fields = [
            ("Тип", self.kind), ("Категория", self.category),
            ("Сумма", self.amount), ("Дата YYYY-MM-DD", self.day),
        ]
        for column, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w")
            form.columnconfigure(column, weight=1)
            if column == 0:
                widget = ttk.Combobox(
                    form, textvariable=variable, values=("Расход", "Доход"),
                    state="readonly", width=15,
                )
            elif column == 1:
                self.category_box = ttk.Combobox(
                    form, textvariable=variable, width=20,
                )
                widget = self.category_box
            else:
                widget = ttk.Entry(form, textvariable=variable, width=18)
            widget.grid(row=1, column=column, sticky="ew", padx=(0, 8))
        ttk.Label(form, text="Описание (необязательно)").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 0),
        )
        ttk.Entry(form, textvariable=self.description).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=(0, 8),
        )
        self.submit_button = ttk.Button(
            form, text="Добавить", command=self.add,
        )
        self.submit_button.grid(
            row=3, column=3, sticky="ew",
        )
        table_frame = ttk.Frame(panel)
        table_frame.pack(fill="both", expand=True, pady=16)
        columns = ("date", "type", "category", "amount", "note", "status")
        self.table = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse",
        )
        headings = ("Дата", "Тип", "Категория", "Сумма", "Описание", "Статус")
        for column, heading in zip(columns, headings):
            self.table.heading(column, text=heading)
            self.table.column(column, width=110, minwidth=70)
        self.table.column("amount", anchor="e")
        self.table.column("note", width=200)
        scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview,
        )
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.tag_configure("cancelled", foreground="#777777")
        actions = ttk.Frame(panel)
        actions.pack(fill="x")
        ttk.Button(actions, text="Редактировать выбранную",
               command=self.edit).pack(side="left")
        ttk.Button(actions, text="Отменить выбранную",
                   command=self.cancel).pack(side="left")
        ttk.Button(actions, text="Сохранить",
                   command=self.save).pack(side="right")
        self.status = tk.StringVar(value="Изменения сохраняются автоматически")
        ttk.Label(panel, textvariable=self.status).pack(
            anchor="w", pady=(8, 0),
        )
        self.refresh()

    def refresh(self) -> None:
        """Обновить баланс и строки после изменения объектов."""
        self.balance.set(
            f"Баланс: {calculate_net_balance(self.transactions, 0):,.2f} ₽",
        )
        self.category_box["values"] = [c.name for c in self.categories]
        for row in self.table.get_children():
            self.table.delete(row)
        for index, item in enumerate(self.transactions):
            self.table.insert("", 0, iid=str(index), values=(
                item.date, "Доход" if item.type == "income" else "Расход",
                item.category.name, f"{item.amount:.2f}", item.description,
                "Отменена" if item.is_cancelled else "Активна",
            ), tags=("cancelled",) if item.is_cancelled else ())

    def add(self) -> None:
        """Проверить форму, создать объект и сохранить данные."""
        try:
            name = self.category.get().strip()
            category = find_category(self.categories, name) or Category(name)
            amount = float(self.amount.get().strip().replace(",", "."))
            day = datetime.strptime(self.day.get().strip(), "%Y-%m-%d")
            identifier = (
                self.transactions[self.editing_index].id
                if self.editing_index is not None
                else max((t.id for t in self.transactions), default=0) + 1
            )
            item = Transaction(
                identifier, amount, category, day.date().isoformat(),
                self.description.get().strip(),
                "income" if self.kind.get() == "Доход" else "expense",
            )
        except ValueError:
            messagebox.showerror(
                "Проверьте поля",
                "Укажите категорию, положительную конечную сумму "
                "и корректную дату в формате YYYY-MM-DD.", parent=self.root,
            )
            return
        if category not in self.categories:
            self.categories.append(category)
        if self.editing_index is None:
            self.transactions.append(item)
        else:
            item.is_cancelled = self.transactions[
                self.editing_index
            ].is_cancelled
            self.transactions[self.editing_index] = item
            self.editing_index = None
            self.submit_button.configure(text="Добавить")
        self.dirty = True
        self.refresh()
        self.save()
        self.amount.set("")
        self.description.set("")

    def edit(self) -> None:
        """Загрузить выбранную операцию в форму для редактирования."""
        selection = self.table.selection()
        if not selection:
            self.status.set("Выберите операцию в таблице")
            return
        self.editing_index = int(selection[0])
        item = self.transactions[self.editing_index]
        self.kind.set("Доход" if item.type == "income" else "Расход")
        self.category.set(item.category.name)
        self.amount.set(str(item.amount))
        self.day.set(item.date)
        self.description.set(item.description)
        self.submit_button.configure(text="Сохранить изменения")
        self.status.set(f"Редактирование операции #{item.id}")

    def cancel(self) -> None:
        """Отменить выбранную операцию без удаления из истории."""
        selection = self.table.selection()
        if not selection:
            self.status.set("Выберите операцию в таблице")
            return
        self.transactions[int(selection[0])].cancel()
        self.dirty = True
        self.refresh()
        self.save()

    def save(self) -> bool:
        """Сохранить объекты; при ошибке оставить их в памяти."""
        try:
            save_categories(self.data_dir / "categories.json", self.categories)
            save_transactions(
                self.data_dir / "transactions.json", self.transactions,
            )
        except OSError as error:
            self.status.set("Не сохранено. Повторите сохранение.")
            messagebox.showerror("Ошибка сохранения", str(error),
                                 parent=self.root)
            return False
        self.dirty = False
        self.status.set("Данные сохранены")
        return True

    def close(self) -> None:
        """Закрыть окно после сохранения несохранённых изменений."""
        if not self.dirty or self.save():
            self.root.destroy()


def main() -> None:
    """Открыть приложение с общим для CLI и GUI хранилищем."""
    root = tk.Tk()
    try:
        FinanceApp(root, Path(__file__).parent / "data")
    except (OSError, ValueError, TypeError, KeyError) as error:
        messagebox.showerror("Не удалось загрузить данные", str(error),
                             parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
