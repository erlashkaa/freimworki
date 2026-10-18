import json

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from finance.models import Category, Transaction


@pytest.mark.django_db
def test_import_links_objects_and_prevents_duplicates(tmp_path):
    user = User.objects.create_user("importer")
    (tmp_path / "categories.json").write_text(
        json.dumps({"Food": 500}), encoding="utf-8",
    )
    (tmp_path / "transactions.json").write_text(json.dumps([{
        "id": 9, "category": "Food", "amount": 100, "type": "expense",
        "date": "2026-10-18", "description": "Lunch", "is_cancelled": True,
    }]), encoding="utf-8")
    call_command("import_json", user.username, directory=tmp_path)
    item = Transaction.objects.get()
    assert item.category.owner == user
    assert item.category.name == "Food"
    assert item.is_cancelled
    with pytest.raises(CommandError):
        call_command("import_json", user.username, directory=tmp_path)
    assert Transaction.objects.count() == 1


@pytest.mark.django_db
def test_failed_import_rolls_back_everything(tmp_path):
    user = User.objects.create_user("importer")
    (tmp_path / "categories.json").write_text(
        '{"Food": 500}', encoding="utf-8",
    )
    (tmp_path / "transactions.json").write_text(json.dumps([{
        "category": "Food", "amount": -1, "type": "expense",
        "date": "2026-10-18",
    }]), encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("import_json", user.username, directory=tmp_path)
    assert Category.objects.count() == 0
    assert Transaction.objects.count() == 0
