from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category


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
