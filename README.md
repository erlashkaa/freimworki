# FinanceTracker

## ПР9–11: ORM, Django Admin и Forms

Веб-версия продолжена без создания нового проекта:

- ПР9: модели `Category`, `Transaction`, `LedgerState`, связи, миграции,
  пользовательский `TransactionQuerySet`, поиск, фильтрация, агрегаты,
  аннотации и `Paginator`;
- ПР10: административная панель `/admin/`, поиск и фильтры, связанные
  операции, массовая отмена, URL категорий и вычисляемое поле
  `Transaction.signed_amount`;
- ПР11: `TransactionFilterForm`, `TransactionModelForm`, HTML-страницы
  списка, создания, редактирования и отмены операций с серверной валидацией
  и CSRF-защитой.

После входа дополнительные страницы доступны по адресам:

```text
/operations/
/operations/new/
/categories/<slug>/
/admin/
```

Для входа в административную панель создайте локального администратора:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Для анализа SQL-запросов через Django Debug Toolbar запустите локально:

```powershell
$env:DJANGO_DEBUG="1"
.\.venv\Scripts\python.exe serve.py
```

Основные файлы ПР9–11: `finance/models.py`, `finance/selectors.py`,
`finance/admin.py`, `finance/forms.py`, `finance/views.py`,
`finance/templates/finance/` и `tests/test_pr9_pr11.py`.

## Веб-версия ПР5 и ПР6

Django-приложение с REST API и интерфейсом в браузере: аккаунты, личные
категории, месячные лимиты, доходы и расходы, отмена операций и история.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe serve.py
```

Откройте http://127.0.0.1:8765 и создайте аккаунт. Если окружение уже есть,
первую команду можно пропустить. Следующий запуск: только `serve.py`.
Остановка сервера: Ctrl+C. Пакеты рассчитаны на Python 3.10+.

Веб-версия использует отдельную SQLite-базу в `.local/`. Старые JSON-файлы
используются консольной и оконной версиями. Импорт в пустой веб-аккаунт:
`python manage.py import_json ИМЯ_АККАУНТА --directory data`.

Основные новые файлы:

- `webconfig/` — настройки Django, URL и WSGI.
- `finance/models.py`, `finance/migrations/` — таблицы и миграции.
- `finance/views.py`, `finance/forms.py` — API и проверка запросов.
- `finance/services.py` — сводка и версионирование кэша.
- `finance/templates/finance/index.html` — страница приложения.
- `finance/static/finance/` — CSS и JavaScript с fetch.
- `tests/test_web.py`, `tests/test_import_json.py` — проверки веб-версии.
- `scripts/load_test.py` — нагрузочная проверка через HTTP.
- `serve.py` — локальное развёртывание через Waitress.

Документация: [API](docs/API.md), [запуск и развёртывание](docs/DEPLOYMENT.md),
[план](docs/PLAN_PR5_PR6.md), [проверки и защита работы](docs/PR5_PR6.md).

## Консольная и оконная версии ПР1–3

Консольное приложение для учёта личных доходов и расходов на Python 3.10+.
В ПР3 функциональная модель ПР2 заменена объектной моделью без изменения
пользовательского сценария.

## Предметная область и ООП модель

`Category` описывает категорию финансовых операций:

- `name: str` — название категории;
- `limit: float | None` — месячный лимит расходов либо отсутствие лимита;
- `from_dict()` и `to_dict()` — преобразование между объектом и JSON-данными;
- `__str__()` — отображение названия и лимита.

`Transaction` описывает доход или расход:

- `id: int` — идентификатор;
- `amount: float` — сумма операции;
- `category: Category` — ссылка на объект категории;
- `date: str` — дата в формате `YYYY-MM-DD`;
- `description: str` — описание операции;
- `type: str` — `income` или `expense`;
- `from_dict()` и `to_dict()` — JSON-сериализация с сохранением в файле
	названия категории, а не ссылки на объект;
- `__str__()` — краткое читаемое представление операции.

## Структура проекта

```text
.
|-- .flake8
|-- data/
|   |-- categories.json
|   `-- transactions.json
|-- main.py
|-- models/
|   |-- __init__.py
|   |-- categories.py
|   `-- transactions.py
|-- requirements.txt
|-- storage.py
|-- tests/
|   |-- test_categories.py
|   |-- test_storage.py
|   `-- test_transactions.py
`-- utils.py
```

- `models/` содержит классы предметной области и функции работы с коллекциями.
- `storage.py` загружает и сохраняет модели в JSON.
- `main.py` реализует меню приложения и работает со списками объектов.
- `utils.py` содержит безопасный ввод чисел и дат.
- `data/` содержит постоянные данные; `tests/` — автоматические тесты.

## Формат хранения JSON

`data/categories.json` хранит отображение названий категорий на лимиты:

```json
{
		"Продукты": 15000.0,
		"Транспорт": 5000.0
}
```

`data/transactions.json` хранит список операций. В поле `category` записывается
название категории, которое при загрузке связывается с объектом `Category`:

```json
{
		"id": 1,
		"type": "expense",
		"category": "Продукты",
		"amount": 1200.0,
		"date": "2026-09-27",
		"description": "Покупки"
}
```

Отсутствующий или повреждённый JSON-файл безопасно загружается как пустая
коллекция. Существующий словарный формат категорий продолжает поддерживаться.

## Установка и запуск

Создайте и активируйте виртуальное окружение, затем установите зависимости:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux или macOS:

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
python main.py
```

В меню доступны баланс и сводка категорий, добавление операции, проверка
лимита и история с фильтрацией по категории либо сортировкой по сумме.

## Тесты и проверка качества

```bash
pytest -v
flake8 .
```

## Соответствие практическим работам

Предметная область — личные финансы: Category заменяет сущность комнаты,
Transaction — операцию бронирования. Связь Transaction.category хранит сам
объект Category; уникальное название категории служит ключом в JSON.

- ПР1: `python examples/pr1.py` — отдельный сценарий с простыми типами,
  датой datetime.date и функцией статуса.
- ПР2: `python examples/pr2.py` — учебный пример list, dict, set, tuple,
  добавления, сортировки и фильтрации. JSON, CLI и обработка ошибок
  реализованы в основных модулях приложения.
- ПР3: основной `main.py` работает с объектами. Category.validate_limit()
  — статический метод проверки, Category.allows() — проверка покупки,
  Transaction.cancel() — отмена. Конструкторы проверяют суммы и лимиты.
  Методы from_dict() являются фабриками классов.

Отменённые операции сохраняются в истории и JSON (поле is_cancelled),
но исключаются из баланса и расходов. В меню пункт 6 отменяет операцию
по ID, показанному в истории. Сводка расходов и проверка лимита относятся
к текущему календарному месяцу. input_int() безопасно читает ID, input_float()
отклоняет NaN и бесконечность. Даты хранятся как строки ISO для совместимости
с существующими данными; input_date() проверяет их через datetime.

### История разработки

Папка была предоставлена уже с реализацией ПР3, без собственного .git.
Первый локальный коммит сохраняет это исходное состояние. Примеры ПР1/ПР2
добавлены позднее как учебные иллюстрации; они не являются историческими
снимками полного приложения. История проверяется командой `git log --oneline`.

В ограниченной среде тесты можно запустить с временной папкой проекта:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.test-tmp
.venv\Scripts\python.exe -m flake8 .
```

## Оконный интерфейс

```powershell
.venv\Scripts\python.exe gui.py
```

Окно показывает баланс и историю операций. Для добавления заполните тип,
категорию (можно ввести новую), сумму и дату; описание необязательно.
Для редактирования выберите строку, нажмите «Редактировать выбранную» и
сохраните изменения кнопкой формы. Для отмены выберите строку и нажмите
«Отменить выбранную».
Изменения автоматически сохраняются в общую с CLI папку data/.
Кнопка «Сохранить» позволяет повторить запись при ошибке.
Не редактируйте данные одновременно через CLI и окно.
Используется стандартный Tkinter, дополнительные Python-пакеты не нужны.
