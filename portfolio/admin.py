from django.contrib import admin

from .models import Cryptocurrency, Portfolio, Transaction


@admin.register(Cryptocurrency)
class CryptocurrencyAdmin(admin.ModelAdmin):
    list_display = ["name", "symbol", "current_price", "last_updated"]
    search_fields = ["name", "symbol", "coingecko_id"]
    list_filter = ["last_updated"]
    ordering = ["name"]


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "cryptocurrency",
        "total_quantity",
        "avg_buy_price",
        "total_invested",
    ]
    search_fields = ["user__username", "cryptocurrency__name", "cryptocurrency__symbol"]
    list_filter = ["cryptocurrency", "user"]
    ordering = ["-total_invested"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "portfolio",
        "transaction_type",
        "quantity",
        "price_per_unit",
        "total_amount",
    ]
    search_fields = ["portfolio__user__username", "portfolio__cryptocurrency__name"]
    list_filter = ["transaction_type", "created_at", "portfolio__cryptocurrency"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
