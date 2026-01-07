from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Portfolio, Transaction


class UserRegisterForm(UserCreationForm):
    """Форма регистрации пользователя."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email"}
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Имя пользователя"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Пароль"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Подтвердите пароль"}
        )


class TransactionForm(forms.ModelForm):
    """Форма добавления транзакции."""

    coingecko_id = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Transaction
        fields = ["transaction_type", "quantity", "price_per_unit", "notes"]
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Количество",
                    "step": "0.00000001",
                    "min": "0.00000001",
                }
            ),
            "price_per_unit": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Цена за единицу (USD)",
                    "step": "0.00000001",
                    "min": "0.00000001",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Заметки (необязательно)",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        quantity = cleaned_data.get("quantity")
        coingecko_id = cleaned_data.get("coingecko_id")

        if transaction_type == "SELL" and self.user and coingecko_id:
            try:
                portfolio = Portfolio.objects.get(
                    user=self.user, cryptocurrency__coingecko_id=coingecko_id
                )
                if quantity and quantity > portfolio.total_quantity:
                    raise forms.ValidationError(
                        f"Недостаточно средств. Доступно: {portfolio.total_quantity}"
                    )
            except Portfolio.DoesNotExist:
                raise forms.ValidationError("У вас нет этой криптовалюты для продажи")

        return cleaned_data


class CryptoSearchForm(forms.Form):
    """Форма поиска криптовалюты."""

    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите название или символ (BTC, ETH...)",
                "autocomplete": "off",
            }
        ),
    )
