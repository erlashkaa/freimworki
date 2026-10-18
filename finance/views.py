import hashlib
import json
from datetime import datetime
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from .forms import CategoryForm, RegisterForm, TransactionForm
from .models import Category, Transaction
from .services import money, summary, touch_ledger


def error(message: str, status: int = 400, **extra) -> JsonResponse:
    return JsonResponse({"error": message, **extra}, status=status)


def api(methods: tuple[str, ...], *, public: bool = False):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = error("Метод не поддерживается", 405)
                response["Allow"] = ", ".join(methods)
                return response
            if not public and not request.user.is_authenticated:
                return error("Необходимо войти", 401)
            if request.method in ("POST", "PATCH"):
                if request.content_type != "application/json":
                    return error("Ожидается application/json", 415)
                try:
                    request.payload = json.loads(request.body)
                except (ValueError, UnicodeDecodeError):
                    return error("Некорректный JSON")
                if not isinstance(request.payload, dict) or any(
                    isinstance(value, (dict, list, bool))
                    for value in request.payload.values()
                ):
                    return error("Ожидается объект с простыми значениями")
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def form_error(form) -> JsonResponse:
    return error("Проверьте введенные данные", fields={
        key: list(value) for key, value in form.errors.items()
    })


def throttle(request, scope: str, limit: int = 30) -> bool:
    address = request.META.get("REMOTE_ADDR", "unknown")
    digest = hashlib.sha256(f"{scope}:{address}".encode()).hexdigest()
    key = f"auth:{digest}"
    if cache.add(key, 1, 300):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, 300)
        return False


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, "finance/index.html")


@api(("GET",), public=True)
def session(request):
    return JsonResponse({
        "user": {"username": request.user.username}
        if request.user.is_authenticated else None,
        "csrfToken": get_token(request),
    })


@api(("POST",), public=True)
def register(request):
    if throttle(request, "register", 10):
        return error("Слишком много попыток. Повторите через 5 минут", 429)
    form = RegisterForm(request.payload)
    if not form.is_valid():
        return form_error(form)
    try:
        with transaction.atomic():
            user = form.save()
    except IntegrityError:
        return error("Имя пользователя уже занято", 409)
    login(request, user)
    return JsonResponse({
        "user": {"username": user.username}, "csrfToken": get_token(request),
    }, status=201)


@api(("POST",), public=True)
def sign_in(request):
    if throttle(request, "login"):
        return error("Слишком много попыток. Повторите через 5 минут", 429)
    username = request.payload.get("username", "")
    password = request.payload.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str):
        return error("Логин и пароль должны быть строками")
    if len(username) > 150 or len(password) > 1024:
        return error("Слишком длинный логин или пароль")
    user = authenticate(request, username=username, password=password)
    if user is None:
        return error("Неверное имя пользователя или пароль", 401)
    login(request, user)
    return JsonResponse({
        "user": {"username": user.username}, "csrfToken": get_token(request),
    })


@api(("POST",))
def sign_out(request):
    logout(request)
    return JsonResponse({"ok": True, "csrfToken": get_token(request)})


def category_data(category) -> dict:
    return {
        "id": category.id, "name": category.name,
        "limit": None if category.limit is None else money(category.limit),
    }


@api(("GET", "POST"))
def categories(request):
    if request.method == "GET":
        return JsonResponse({"results": [category_data(
            c) for c in Category.objects.filter(owner=request.user)]})
    return save_category(request)


@api(("PATCH",))
def category_detail(request, pk: int):
    category = Category.objects.filter(owner=request.user, pk=pk).first()
    if category is None:
        return error("Категория не найдена", 404)
    return save_category(request, category)


def save_category(request, category=None):
    data = category_data(category) if category else {}
    data.update(request.payload)
    form = CategoryForm(data)
    if not form.is_valid():
        return form_error(form)
    creating = category is None
    category = category or Category(owner=request.user)
    category.name = form.cleaned_data["name"]
    category.limit = form.cleaned_data["limit"]
    try:
        with transaction.atomic():
            category.save()
            touch_ledger(request.user)
    except IntegrityError:
        return error("Категория с таким названием уже существует", 409)
    return JsonResponse(
        category_data(category),
        status=201 if creating else 200)


def transaction_data(item) -> dict:
    return {
        "id": item.id, "category": item.category_id,
        "category_name": item.category.name, "amount": money(item.amount),
        "type": item.type, "date": item.date.isoformat(),
        "description": item.description, "is_cancelled": item.is_cancelled,
    }


@api(("GET", "POST"))
def transactions(request):
    if request.method == "POST":
        form = TransactionForm(request.payload, user=request.user)
        if not form.is_valid():
            return form_error(form)
        with transaction.atomic():
            item = Transaction.objects.create(**form.cleaned_data)
            touch_ledger(request.user)
        return JsonResponse(transaction_data(item), status=201)
    items = Transaction.objects.filter(
        category__owner=request.user,
    ).select_related("category")
    try:
        page = int(request.GET.get("page", 1))
        if not 1 <= page <= 100000:
            raise ValueError
        category = request.GET.get("category")
        if category:
            items = items.filter(category_id=int(category))
    except ValueError:
        return error("Некорректный номер страницы или категории")
    month = request.GET.get("month")
    if month:
        try:
            day = datetime.strptime(month, "%Y-%m")
        except ValueError:
            return error("Месяц должен иметь формат YYYY-MM")
        items = items.filter(date__year=day.year, date__month=day.month)
    ordering = request.GET.get("ordering", "-date")
    if ordering not in ("date", "-date", "amount", "-amount"):
        return error("Недопустимый порядок сортировки")
    items = items.order_by(ordering, "-id")
    count = items.count()
    start = (page - 1) * 20
    return JsonResponse({
        "results": [transaction_data(t) for t in items[start:start + 20]],
        "count": count, "page": page, "page_size": 20,
    })


@api(("POST",))
def cancel(request, pk: int):
    with transaction.atomic():
        item = Transaction.objects.filter(
            pk=pk, category__owner=request.user,
        ).select_related("category").first()
        if item is None:
            return error("Операция не найдена", 404)
        if not item.is_cancelled:
            item.is_cancelled = True
            item.save(update_fields=["is_cancelled"])
            touch_ledger(request.user)
    return JsonResponse(transaction_data(item))


@api(("GET",))
def overview(request):
    value = request.GET.get("month", timezone.localdate().strftime("%Y-%m"))
    try:
        month = datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        return error("Месяц должен иметь формат YYYY-MM")
    return JsonResponse(summary(request.user, month))


def csrf_failure(request, reason=""):
    return error("Проверка CSRF не пройдена. Обновите страницу", 403)


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
