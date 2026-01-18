from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .forms import TransactionForm
from .models import Cryptocurrency, Portfolio, Transaction


class CryptocurrencyModelTest(TestCase):
    """Tests for Cryptocurrency model."""

    def setUp(self):
        self.crypto = Cryptocurrency.objects.create(
            coingecko_id="bitcoin",
            symbol="btc",
            name="Bitcoin",
            current_price=Decimal("50000.00"),
            image_url="https://example.com/btc.png",
        )

    def test_cryptocurrency_creation(self):
        """Test cryptocurrency is created correctly."""
        self.assertEqual(self.crypto.coingecko_id, "bitcoin")
        self.assertEqual(self.crypto.symbol, "btc")
        self.assertEqual(self.crypto.name, "Bitcoin")
        self.assertEqual(self.crypto.current_price, Decimal("50000.00"))

    def test_cryptocurrency_str(self):
        """Test cryptocurrency string representation."""
        self.assertEqual(str(self.crypto), "Bitcoin (BTC)")

    def test_cryptocurrency_unique_coingecko_id(self):
        """Test that coingecko_id must be unique."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Cryptocurrency.objects.create(
                coingecko_id="bitcoin",
                symbol="btc2",
                name="Bitcoin 2",
            )


class PortfolioModelTest(TestCase):
    """Tests for Portfolio model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.crypto = Cryptocurrency.objects.create(
            coingecko_id="ethereum",
            symbol="eth",
            name="Ethereum",
            current_price=Decimal("3000.00"),
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            cryptocurrency=self.crypto,
            total_quantity=Decimal("2.5"),
            avg_buy_price=Decimal("2000.00"),
            total_invested=Decimal("5000.00"),
        )

    def test_portfolio_creation(self):
        """Test portfolio is created correctly."""
        self.assertEqual(self.portfolio.user, self.user)
        self.assertEqual(self.portfolio.cryptocurrency, self.crypto)
        self.assertEqual(self.portfolio.total_quantity, Decimal("2.5"))

    def test_portfolio_str(self):
        """Test portfolio string representation."""
        self.assertEqual(str(self.portfolio), "testuser - ETH")

    def test_current_value_calculation(self):
        """Test current value property calculation."""
        expected_value = Decimal("2.5") * Decimal("3000.00")
        self.assertEqual(self.portfolio.current_value, expected_value)

    def test_profit_loss_calculation(self):
        """Test profit/loss calculation."""
        current_value = Decimal("2.5") * Decimal("3000.00")
        expected_pl = current_value - Decimal("5000.00")
        self.assertEqual(self.portfolio.profit_loss, expected_pl)

    def test_profit_loss_percent_calculation(self):
        """Test profit/loss percentage calculation."""
        current_value = Decimal("2.5") * Decimal("3000.00")
        profit_loss = current_value - Decimal("5000.00")
        expected_percent = (profit_loss / Decimal("5000.00")) * 100
        self.assertEqual(self.portfolio.profit_loss_percent, expected_percent)

    def test_profit_loss_percent_zero_invested(self):
        """Test profit/loss percentage when nothing invested."""
        self.portfolio.total_invested = Decimal("0")
        self.portfolio.save()
        self.assertEqual(self.portfolio.profit_loss_percent, Decimal("0"))

    def test_portfolio_unique_user_crypto(self):
        """Test that user can have only one portfolio per cryptocurrency."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Portfolio.objects.create(
                user=self.user,
                cryptocurrency=self.crypto,
                total_quantity=Decimal("1.0"),
            )


class TransactionModelTest(TestCase):
    """Tests for Transaction model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.crypto = Cryptocurrency.objects.create(
            coingecko_id="bitcoin",
            symbol="btc",
            name="Bitcoin",
            current_price=Decimal("50000.00"),
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            cryptocurrency=self.crypto,
        )

    def test_transaction_creation_buy(self):
        """Test buy transaction is created correctly."""
        transaction = Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="BUY",
            quantity=Decimal("0.5"),
            price_per_unit=Decimal("40000.00"),
        )
        self.assertEqual(transaction.transaction_type, "BUY")
        self.assertEqual(transaction.quantity, Decimal("0.5"))
        self.assertEqual(transaction.total_amount, Decimal("20000.00"))

    def test_transaction_str(self):
        """Test transaction string representation."""
        transaction = Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="BUY",
            quantity=Decimal("1.0"),
            price_per_unit=Decimal("50000.00"),
        )
        self.assertEqual(str(transaction), "Покупка 1.0 BTC")

    def test_total_amount_auto_calculation(self):
        """Test that total_amount is calculated automatically on save."""
        transaction = Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="BUY",
            quantity=Decimal("2.0"),
            price_per_unit=Decimal("45000.00"),
        )
        self.assertEqual(transaction.total_amount, Decimal("90000.00"))

    def test_portfolio_recalculation_on_buy(self):
        """Test portfolio is recalculated after buy transaction."""
        Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="BUY",
            quantity=Decimal("1.0"),
            price_per_unit=Decimal("40000.00"),
        )
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.total_quantity, Decimal("1.0"))
        self.assertEqual(self.portfolio.avg_buy_price, Decimal("40000.00"))
        self.assertEqual(self.portfolio.total_invested, Decimal("40000.00"))

    def test_portfolio_recalculation_on_sell(self):
        """Test portfolio is recalculated after sell transaction."""
        Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="BUY",
            quantity=Decimal("2.0"),
            price_per_unit=Decimal("40000.00"),
        )
        Transaction.objects.create(
            portfolio=self.portfolio,
            transaction_type="SELL",
            quantity=Decimal("0.5"),
            price_per_unit=Decimal("50000.00"),
        )
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.total_quantity, Decimal("1.5"))


class TransactionFormTest(TestCase):
    """Tests for TransactionForm validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.crypto = Cryptocurrency.objects.create(
            coingecko_id="bitcoin",
            symbol="btc",
            name="Bitcoin",
            current_price=Decimal("50000.00"),
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            cryptocurrency=self.crypto,
            total_quantity=Decimal("1.0"),
            avg_buy_price=Decimal("40000.00"),
            total_invested=Decimal("40000.00"),
        )

    def test_valid_buy_transaction(self):
        """Test valid buy transaction form."""
        form_data = {
            "coingecko_id": "bitcoin",
            "transaction_type": "BUY",
            "quantity": "0.5",
            "price_per_unit": "45000.00",
            "transaction_date": "2024-01-15",
            "notes": "",
        }
        form = TransactionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_valid_sell_transaction(self):
        """Test valid sell transaction (has enough balance)."""
        form_data = {
            "coingecko_id": "bitcoin",
            "transaction_type": "SELL",
            "quantity": "0.5",
            "price_per_unit": "50000.00",
            "transaction_date": "2024-01-15",
            "notes": "",
        }
        form = TransactionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_sell_more_than_owned(self):
        """Test sell validation fails when selling more than owned."""
        form_data = {
            "coingecko_id": "bitcoin",
            "transaction_type": "SELL",
            "quantity": "2.0",
            "price_per_unit": "50000.00",
            "transaction_date": "2024-01-15",
            "notes": "",
        }
        form = TransactionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Недостаточно средств", str(form.errors))

    def test_sell_crypto_not_owned(self):
        """Test sell validation fails when user doesn't own the crypto."""
        form_data = {
            "coingecko_id": "ethereum",
            "transaction_type": "SELL",
            "quantity": "1.0",
            "price_per_unit": "3000.00",
            "transaction_date": "2024-01-15",
            "notes": "",
        }
        form = TransactionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("нет этой криптовалюты", str(form.errors))


class ViewsTest(TestCase):
    """Tests for views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.crypto = Cryptocurrency.objects.create(
            coingecko_id="bitcoin",
            symbol="btc",
            name="Bitcoin",
            current_price=Decimal("50000.00"),
        )

    def test_dashboard_requires_login(self):
        """Test dashboard redirects to login when not authenticated."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_dashboard_accessible_when_logged_in(self):
        """Test dashboard is accessible for authenticated users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portfolio/dashboard.html")

    def test_add_transaction_requires_login(self):
        """Test add_transaction redirects to login when not authenticated."""
        response = self.client.get(reverse("add_transaction"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_add_transaction_accessible_when_logged_in(self):
        """Test add_transaction is accessible for authenticated users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("add_transaction"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portfolio/add_transaction.html")

    def test_transaction_list_requires_login(self):
        """Test transaction_list redirects to login when not authenticated."""
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_transaction_list_accessible_when_logged_in(self):
        """Test transaction_list is accessible for authenticated users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portfolio/transaction_list.html")

    def test_register_page_accessible(self):
        """Test register page is accessible."""
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_accessible(self):
        """Test login page is accessible."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_api_update_prices_requires_login(self):
        """Test API endpoint requires authentication."""
        response = self.client.get(reverse("api_update_prices"))
        self.assertEqual(response.status_code, 302)

    def test_api_update_prices_returns_json(self):
        """Test API endpoint returns JSON when authenticated."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("api_update_prices"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")


class RegistrationTest(TestCase):
    """Tests for user registration."""

    def setUp(self):
        self.client = Client()

    def test_user_registration(self):
        """Test user can register successfully."""
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "complexpass123!",
                "password2": "complexpass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_registration_password_mismatch(self):
        """Test registration fails with password mismatch."""
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "complexpass123!",
                "password2": "differentpass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
