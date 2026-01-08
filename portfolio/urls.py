from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Основные страницы
    path("", views.dashboard, name="dashboard"),
    path("add/", views.add_transaction, name="add_transaction"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    # API для AJAX
    path("api/prices/update/", views.api_update_prices, name="api_update_prices"),
    path("api/crypto/search/", views.api_search_crypto, name="api_search_crypto"),
    path('api/crypto/search/', views.api_search_crypto, name='api_search_crypto'),
]
