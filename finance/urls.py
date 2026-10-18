from django.urls import path

from . import views

urlpatterns = [
    path("", views.index),
    path("health/", views.health),
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
