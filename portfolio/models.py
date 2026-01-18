from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Cryptocurrency(models.Model):
    """Справочник криптовалют с данными из CoinGecko API."""

    coingecko_id = models.CharField(
        max_length=100, unique=True, verbose_name="CoinGecko ID"
    )
    symbol = models.CharField(max_length=20, verbose_name="Символ")
    name = models.CharField(max_length=100, verbose_name="Название")
    current_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0"),
        verbose_name="Текущая цена (USD)",
    )
    image_url = models.URLField(blank=True, null=True, verbose_name="URL иконки")
    last_updated = models.DateTimeField(
        auto_now=True, verbose_name="Последнее обновление"
    )

    class Meta:
        verbose_name = "Криптовалюта"
        verbose_name_plural = "Криптовалюты"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.symbol.upper()})"


class Portfolio(models.Model):
    """Позиция пользователя по конкретной криптовалюте."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="Пользователь",
    )
    cryptocurrency = models.ForeignKey(
        Cryptocurrency,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="Криптовалюта",
    )
    total_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0"),
        verbose_name="Общее количество",
    )
    avg_buy_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0"),
        verbose_name="Средняя цена покупки (USD)",
    )
    total_invested = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Всего инвестировано (USD)",
    )

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        unique_together = ["user", "cryptocurrency"]
        ordering = ["-total_invested"]

    def __str__(self):
        return f"{self.user.username} - {self.cryptocurrency.symbol.upper()}"

    @property
    def current_value(self):
        """Текущая стоимость позиции."""
        return self.total_quantity * self.cryptocurrency.current_price

    @property
    def profit_loss(self):
        """Прибыль/убыток в USD."""
        return self.current_value - self.total_invested

    @property
    def profit_loss_percent(self):
        """Прибыль/убыток в процентах."""
        if self.total_invested > 0:
            return (self.profit_loss / self.total_invested) * 100
        return Decimal("0")

    def recalculate(self):
        """Пересчитывает позицию на основе всех транзакций."""
        buy_transactions = self.transactions.filter(transaction_type="BUY")
        sell_transactions = self.transactions.filter(transaction_type="SELL")

        total_bought_qty = sum(t.quantity for t in buy_transactions)
        total_bought_value = sum(t.total_amount for t in buy_transactions)

        total_sold_qty = sum(t.quantity for t in sell_transactions)

        self.total_quantity = total_bought_qty - total_sold_qty

        if total_bought_qty > 0:
            self.avg_buy_price = total_bought_value / total_bought_qty
        else:
            self.avg_buy_price = Decimal("0")

        self.total_invested = self.total_quantity * self.avg_buy_price
        self.save()


class Transaction(models.Model):
    """История транзакций (покупка/продажа)."""

    TRANSACTION_TYPES = [
        ("BUY", "Покупка"),
        ("SELL", "Продажа"),
    ]

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Портфель",
    )
    transaction_type = models.CharField(
        max_length=4, choices=TRANSACTION_TYPES, verbose_name="Тип транзакции"
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Количество",
    )
    price_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        verbose_name="Цена за единицу (USD)",
    )
    total_amount = models.DecimalField(
        max_digits=20, decimal_places=2, verbose_name="Общая сумма (USD)"
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")
    transaction_date = models.DateField(default=timezone.now, verbose_name="Дата транзакции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.quantity} {self.portfolio.cryptocurrency.symbol.upper()}"

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)
        self.portfolio.recalculate()
