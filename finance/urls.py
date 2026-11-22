from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.index, name="home"),
    path("health/", views.health, name="health"),
    path("operations/", views.transaction_list, name="transaction-list"),
    path(
        "operations/new/", views.transaction_create,
        name="transaction-create",
    ),
    path(
        "operations/<int:pk>/edit/", views.transaction_edit,
        name="transaction-edit",
    ),
    path(
        "operations/<int:pk>/cancel/", views.transaction_cancel_form,
        name="transaction-cancel",
    ),
    path(
        "categories/<str:slug>/", views.category_detail_page,
        name="category-detail-page",
    ),
    path("api/session/", views.session),
    path("api/register/", views.register),
    path("api/login/", views.sign_in),
    path("api/logout/", views.sign_out),
    path("api/categories/", views.categories),
    path("api/categories/<int:pk>/", views.category_detail),
    path("api/transactions/", views.transactions),
    path("api/transactions/<int:pk>/cancel/", views.cancel),
    path("api/summary/", views.overview),
]
