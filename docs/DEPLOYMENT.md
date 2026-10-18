# Запуск и развёртывание

## Локальный сервер Windows

Из корневой папки проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe serve.py --port 8765
```

Открыть http://127.0.0.1:8765 и зарегистрировать аккаунт.
Остановка — Ctrl+C. Для следующего запуска достаточно последней команды.
Если .venv уже создано, повторять первую команду не требуется.
Если порт занят, указать другой через --port. Сервер слушает только localhost.

Waitress запускается одним процессом с четырьмя потоками. WhiteNoise отдаёт
CSS и JavaScript. SQLite хранится в `.local/finance.sqlite3`, случайный
локальный ключ — в `.local/secret.key`. Эта папка исключена из Git.
Файл .env автоматически не загружается: настройки читаются из окружения.

CLI `python main.py` и Tkinter `python gui.py` по-прежнему используют data/*.json.
Веб-аккаунты используют отдельную базу. Для переноса старых данных сначала
создать пустой аккаунт в браузере, затем выполнить:

```powershell
.\.venv\Scripts\python.exe manage.py import_json ИМЯ_АККАУНТА --directory data
```

Импорт разрешён только в аккаунт без категорий. При ошибке весь импорт
откатывается. Старые файлы сохраняются; автоматической синхронизации нет.
Числовые ID операций назначаются базой заново.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.test-tmp-final
.\.venv\Scripts\python.exe -m flake8 --jobs=1 .
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

При запущенном сервере, во втором терминале:

```powershell
.\.venv\Scripts\python.exe scripts/load_test.py --url http://127.0.0.1:8765 --requests 200 --workers 8 --output build/load-test.json
```

Скрипт создаёт отдельный тестовый аккаунт со случайным паролем и 20 операциями,
затем проверяет содержимое ответов на 200 параллельных запросов сводки/истории.
Показатели описывают локальный учебный сценарий, а не предельную нагрузку.
Аккаунт остаётся в локальной БД. Не запускать без разрешения на чужом сервере.

## Публичное размещение

Публичный хостинг не настроен: в задании не предоставлен сервер или домен.
Для размещения требуется HTTPS-прокси, например nginx, перед Waitress.
Деплой выполнять под отдельным системным пользователем.

Переменные окружения:

| Переменная | Значение |
|---|---|
| FINANCE_ENV | production |
| DJANGO_SECRET_KEY | Случайная секретная строка не короче 50 символов |
| DJANGO_ALLOWED_HOSTS | Реальный домен без схемы, несколько через запятую |
| DJANGO_CSRF_TRUSTED_ORIGINS | https://ваш-домен |
| FINANCE_DB | Абсолютный путь к SQLite в постоянном хранилище |

В production включены HTTPS redirect, Secure cookies, HSTS и запрещён DEBUG.
Сначала выполнить migrate, collectstatic и `manage.py check --deploy` с этими
настройками. Секреты не помещать в Git.

Пример запуска за доверенным локальным TLS-прокси:

```text
waitress-serve --listen=127.0.0.1:8765 --threads=4 --max-request-body-size=16384 --trusted-proxy=127.0.0.1 --trusted-proxy-headers=x-forwarded-proto webconfig.wsgi:application
```

Прокси должен удалять присланный клиентом X-Forwarded-Proto и устанавливать
собственный. Пример для настроенного HTTPS server-блока nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8765;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 16k;
}
```

TLS-сертификат и домен настраиваются на выбранном сервере. Не включать
production для обычного локального HTTP без TLS-прокси.

## Ограничения учебного развёртывания

SQLite сериализует записи (IMMEDIATE, timeout 20 секунд). Для интенсивной
многопользовательской записи нужен PostgreSQL. LocMemCache и ограничение
попыток входа действуют в одном процессе; для нескольких процессов нужен
общий Redis и ограничение запросов на прокси. За прокси текущий лимитер
видит адрес прокси, поэтому ограничение общее для клиентов этого прокси.
На публичном сервере следует отдельно настроить лимитер по реальному IP
на доверенном прокси. Заголовок X-Forwarded-For приложению не доверяется.

Резервная копия: остановить сервер и сохранить `.local/finance.sqlite3` и
секретный ключ в защищённое хранилище. Срок жизни кэша не заменяет резервирование.
Истёкшие сессии удаляются командой `manage.py clearsessions`.

Основание настроек: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/),
[кэширование](https://docs.djangoproject.com/en/5.2/topics/cache/),
[Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html).
