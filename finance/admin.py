from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import Category, LedgerState, Transaction
from .services import touch_ledger


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ("date", "type", "amount", "description", "is_cancelled")
    readonly_fields = ("date", "type", "amount", "description")
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "limit", "operation_count")
    list_display_links = ("name",)
    search_fields = ("name", "owner__username")
    list_filter = ("owner",)
    ordering = ("owner__username", "name")
    list_per_page = 25
    readonly_fields = ("slug",)
    inlines = (TransactionInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner").annotate(
            _operation_count=Count("transactions"),
        )

    @admin.display(description="операций", ordering="_operation_count")
    def operation_count(self, obj):
        return obj._operation_count

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        touch_ledger(obj.owner)

    def delete_model(self, request, obj):
        owner = obj.owner
        super().delete_model(request, obj)
        touch_ledger(owner)

    def delete_queryset(self, request, queryset):
        owner_ids = list(queryset.values_list(
            "owner_id", flat=True,
        ).distinct())
        super().delete_queryset(request, queryset)
        for owner in get_user_model().objects.filter(pk__in=owner_ids):
            touch_ledger(owner)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        touch_ledger(form.instance.owner)


@admin.action(description="Отменить выбранные операции")
def cancel_transactions(modeladmin, request, queryset):
    owner_ids = list(queryset.values_list(
        "category__owner_id", flat=True,
    ).distinct())
    queryset.update(is_cancelled=True)
    for owner in get_user_model().objects.filter(pk__in=owner_ids):
        touch_ledger(owner)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date", "type", "category", "owner_name", "amount",
        "signed_amount", "is_cancelled",
    )
    list_display_links = ("date", "category")
    list_filter = ("type", "is_cancelled", "date", "category")
    search_fields = (
        "description", "category__name", "category__owner__username",
    )
    ordering = ("-date", "-id")
    list_per_page = 25
    readonly_fields = ("signed_amount",)
    list_editable = ("is_cancelled",)
    actions = (cancel_transactions,)
    autocomplete_fields = ("category",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "category", "category__owner",
        )

    @admin.display(
        description="владелец", ordering="category__owner__username",
    )
    def owner_name(self, obj):
        return obj.category.owner.username

    def save_model(self, request, obj, form, change):
        previous_owner = None
        if change:
            previous_owner = Transaction.objects.select_related(
                "category__owner",
            ).get(pk=obj.pk).category.owner
        super().save_model(request, obj, form, change)
        touch_ledger(obj.category.owner)
        if previous_owner and previous_owner != obj.category.owner:
            touch_ledger(previous_owner)

    def delete_model(self, request, obj):
        owner = obj.category.owner
        super().delete_model(request, obj)
        touch_ledger(owner)

    def delete_queryset(self, request, queryset):
        owner_ids = list(queryset.values_list(
            "category__owner_id", flat=True,
        ).distinct())
        super().delete_queryset(request, queryset)
        for owner in get_user_model().objects.filter(pk__in=owner_ids):
            touch_ledger(owner)


@admin.register(LedgerState)
class LedgerStateAdmin(admin.ModelAdmin):
    list_display = ("owner", "revision")
    search_fields = ("owner__username",)
    readonly_fields = ("owner", "revision")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
