# Реализация ПР9–11 в FinanceTracker

## ПР9 — Django ORM

- `Category.owner` и `Transaction.category` задают связи `ForeignKey`.
- `TransactionQuerySet` реализует `active()`, `owned_by()` и `search()`.
- `finance/selectors.py` содержит составные фильтры, `exclude()`,
  `select_related()`, `annotate()`, `values()`, `Count()` и `Sum()`.
- `finance/services.py` использует `aggregate()`, группировку и кэш сводки.
- API и HTML-список используют `Paginator`; ошибки параметров обрабатываются.

## ПР10 — административная панель

- `/admin/` подключён через стандартное приложение Django Admin.
- `finance/admin.py` настраивает списки, поиск, фильтры, сортировку,
  связанные объекты, пагинацию и массовую отмену операций.
- `Category.slug` и `get_absolute_url()` формируют адрес страницы категории.
- `Transaction.signed_amount` — сохраняемое `GeneratedField`, вычисляемое БД.
- Контекстный процессор передаёт число категорий в общую часть HTML-страниц.
- При `DJANGO_DEBUG=1` подключается Django Debug Toolbar для анализа SQL.

## ПР11 — Django Forms

- `TransactionFilterForm` проверяет поиск, категорию, месяц, тип и сортировку.
- `TransactionModelForm` создаёт и редактирует операции, ограничивает список
  категорий владельцем и отклоняет будущую дату.
- Изменяющие HTML-формы используют POST и `{% csrf_token %}`.
- Чужие операции недоступны благодаря `owned_by(request.user)` и 404.

## Проверка

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flake8 --jobs=1 .
```
