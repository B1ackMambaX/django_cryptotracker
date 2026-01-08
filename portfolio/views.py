from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import CryptoSearchForm, TransactionForm, UserRegisterForm
from .models import Cryptocurrency, Portfolio, Transaction
from .services import CoinGeckoService


def register(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserRegisterForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    """Главная страница - обзор портфеля."""
    portfolios = Portfolio.objects.filter(
        user=request.user, total_quantity__gt=0
    ).select_related("cryptocurrency")

    if portfolios.exists():
        cryptos = [p.cryptocurrency for p in portfolios]
        CoinGeckoService.update_cryptocurrency_prices(cryptos)
        portfolios = Portfolio.objects.filter(
            user=request.user, total_quantity__gt=0
        ).select_related("cryptocurrency")

    total_invested = sum(p.total_invested for p in portfolios)
    total_current_value = sum(p.current_value for p in portfolios)
    total_profit_loss = total_current_value - total_invested

    if total_invested > 0:
        total_profit_loss_percent = (total_profit_loss / total_invested) * 100
    else:
        total_profit_loss_percent = Decimal("0")

    context = {
        "portfolios": portfolios,
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_profit_loss": total_profit_loss,
        "total_profit_loss_percent": total_profit_loss_percent,
    }

    return render(request, "portfolio/dashboard.html", context)


@login_required
def add_transaction(request):
    """Добавление новой транзакции."""
    search_form = CryptoSearchForm()
    transaction_form = TransactionForm(user=request.user)
    search_results = []
    selected_crypto = None

    if request.method == "POST":
        if "search" in request.POST:
            search_form = CryptoSearchForm(request.POST)
            if search_form.is_valid():
                query = search_form.cleaned_data["query"]
                search_results = CoinGeckoService.search_crypto(query)

        elif "select_crypto" in request.POST:
            coingecko_id = request.POST.get("coingecko_id")
            crypto = CoinGeckoService.get_or_create_cryptocurrency(coingecko_id)
            if crypto:
                selected_crypto = crypto
                transaction_form = TransactionForm(
                    user=request.user, initial={"coingecko_id": coingecko_id}
                )

        elif "submit_transaction" in request.POST:
            transaction_form = TransactionForm(request.POST, user=request.user)
            if transaction_form.is_valid():
                coingecko_id = transaction_form.cleaned_data["coingecko_id"]
                crypto = CoinGeckoService.get_or_create_cryptocurrency(coingecko_id)

                if crypto:
                    portfolio, created = Portfolio.objects.get_or_create(
                        user=request.user, cryptocurrency=crypto
                    )

                    transaction = transaction_form.save(commit=False)
                    transaction.portfolio = portfolio
                    transaction.save()

                    return redirect("dashboard")

    context = {
        "search_form": search_form,
        "transaction_form": transaction_form,
        "search_results": search_results,
        "selected_crypto": selected_crypto,
    }

    return render(request, "portfolio/add_transaction.html", context)


@login_required
def transaction_list(request):
    """История транзакций пользователя."""
    transactions = (
        Transaction.objects.filter(portfolio__user=request.user)
        .select_related("portfolio__cryptocurrency")
        .order_by("-created_at")
    )

    return render(
        request, "portfolio/transaction_list.html", {"transactions": transactions}
    )


@login_required
def api_update_prices(request):
    """API endpoint для AJAX обновления цен."""
    portfolios = Portfolio.objects.filter(
        user=request.user, total_quantity__gt=0
    ).select_related("cryptocurrency")

    if portfolios.exists():
        cryptos = [p.cryptocurrency for p in portfolios]
        CoinGeckoService.update_cryptocurrency_prices(cryptos)

    portfolios = Portfolio.objects.filter(
        user=request.user, total_quantity__gt=0
    ).select_related("cryptocurrency")

    data = {"portfolios": [], "totals": {}}

    total_invested = Decimal("0")
    total_current_value = Decimal("0")

    for p in portfolios:
        current_value = p.current_value
        profit_loss = p.profit_loss
        profit_loss_percent = p.profit_loss_percent

        total_invested += p.total_invested
        total_current_value += current_value

        data["portfolios"].append(
            {
                "id": p.id,
                "symbol": p.cryptocurrency.symbol.upper(),
                "current_price": float(p.cryptocurrency.current_price),
                "current_value": float(current_value),
                "profit_loss": float(profit_loss),
                "profit_loss_percent": float(profit_loss_percent),
            }
        )

    total_profit_loss = total_current_value - total_invested
    if total_invested > 0:
        total_profit_loss_percent = (total_profit_loss / total_invested) * 100
    else:
        total_profit_loss_percent = Decimal("0")

    data["totals"] = {
        "total_invested": float(total_invested),
        "total_current_value": float(total_current_value),
        "total_profit_loss": float(total_profit_loss),
        "total_profit_loss_percent": float(total_profit_loss_percent),
    }

    return JsonResponse(data)


@login_required
def api_search_crypto(request):
    """API endpoint для AJAX поиска криптовалют."""
    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"results": []})

    results = CoinGeckoService.search_crypto(query)
    return JsonResponse({"results": results})
