from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Category, Transaction


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username"]


class CategoryForm(forms.Form):
    name = forms.CharField(max_length=80)
    limit = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False,
    )


class TransactionForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.none())
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"),
    )
    type = forms.ChoiceField(
        choices=[("income", "Доход"), ("expense", "Расход")])
    date = forms.DateField(input_formats=["%Y-%m-%d"])
    description = forms.CharField(max_length=300, required=False)

    def __init__(self, data, *, user):
        super().__init__(data)
        self.fields["category"].queryset = Category.objects.filter(owner=user)


class TransactionFilterForm(forms.Form):
    ORDERING = [
        ("-date", "Сначала новые"), ("date", "Сначала старые"),
        ("-amount", "Сумма по убыванию"),
        ("amount", "Сумма по возрастанию"),
    ]
    query = forms.CharField(
        label="Поиск", max_length=100, required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Описание или категория"}),
    )
    category = forms.ModelChoiceField(
        label="Категория", queryset=Category.objects.none(), required=False,
        empty_label="Все категории",
    )
    month = forms.DateField(
        label="Месяц", required=False, input_formats=["%Y-%m"],
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month"}),
    )
    type = forms.ChoiceField(
        label="Тип", required=False,
        choices=[("", "Все типы"), *
                 Transaction._meta.get_field("type").choices],
    )
    include_cancelled = forms.BooleanField(
        label="Показывать отменённые", required=False,
    )
    ordering = forms.ChoiceField(
        label="Сортировка", choices=ORDERING, required=False,
    )

    def __init__(self, data=None, *, user):
        super().__init__(data)
        self.fields["category"].queryset = Category.objects.filter(owner=user)


class TransactionModelForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["type", "amount", "category", "date", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(attrs={
                "placeholder": "Назначение операции",
            }),
        }

    def __init__(self, data=None, *, user, instance=None):
        super().__init__(data=data, instance=instance)
        self.user = user
        self.fields["category"].queryset = Category.objects.filter(owner=user)
        self.fields["category"].empty_label = "Выберите категорию"

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value > timezone.localdate():
            raise forms.ValidationError(
                "Дата операции не может быть в будущем.")
        return value

    def clean_category(self):
        category = self.cleaned_data["category"]
        if category.owner_id != self.user.id:
            raise forms.ValidationError("Выберите категорию своего аккаунта.")
        return category
