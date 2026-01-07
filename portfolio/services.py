from datetime import timedelta
from decimal import Decimal

import requests
from django.utils import timezone


class CoinGeckoService:
    """Сервис для работы с CoinGecko API."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_TIMEOUT = timedelta(seconds=60)

    _price_cache = {}
    _cache_time = None

    @classmethod
    def search_crypto(cls, query):
        """Поиск криптовалюты по названию или символу."""
        try:
            response = requests.get(
                f"{cls.BASE_URL}/search", params={"query": query}, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("coins", [])[:10]
        except requests.RequestException:
            return []

    @classmethod
    def get_crypto_info(cls, coingecko_id):
        """Получить информацию о криптовалюте по ID."""
        try:
            response = requests.get(
                f"{cls.BASE_URL}/coins/{coingecko_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    @classmethod
    def get_price(cls, coingecko_id):
        """Получить текущую цену криптовалюты в USD."""
        now = timezone.now()

        if (
            cls._cache_time
            and now - cls._cache_time < cls.CACHE_TIMEOUT
            and coingecko_id in cls._price_cache
        ):
            return cls._price_cache[coingecko_id]

        try:
            response = requests.get(
                f"{cls.BASE_URL}/simple/price",
                params={"ids": coingecko_id, "vs_currencies": "usd"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if coingecko_id in data:
                price = Decimal(str(data[coingecko_id]["usd"]))
                cls._price_cache[coingecko_id] = price
                cls._cache_time = now
                return price
        except (requests.RequestException, KeyError, ValueError):
            pass

        return None

    @classmethod
    def get_prices_bulk(cls, coingecko_ids):
        """Получить цены для нескольких криптовалют."""
        if not coingecko_ids:
            return {}

        try:
            ids_str = ",".join(coingecko_ids)
            response = requests.get(
                f"{cls.BASE_URL}/simple/price",
                params={"ids": ids_str, "vs_currencies": "usd"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            prices = {}
            for coin_id, price_data in data.items():
                if "usd" in price_data:
                    prices[coin_id] = Decimal(str(price_data["usd"]))

            cls._price_cache.update(prices)
            cls._cache_time = timezone.now()

            return prices
        except requests.RequestException:
            return {}

    @classmethod
    def update_cryptocurrency_prices(cls, cryptocurrencies):
        """Обновить цены для списка криптовалют в БД."""
        if not cryptocurrencies:
            return

        coingecko_ids = [c.coingecko_id for c in cryptocurrencies]
        prices = cls.get_prices_bulk(coingecko_ids)

        for crypto in cryptocurrencies:
            if crypto.coingecko_id in prices:
                crypto.current_price = prices[crypto.coingecko_id]
                crypto.save(update_fields=["current_price", "last_updated"])

    @classmethod
    def get_or_create_cryptocurrency(cls, coingecko_id):
        """Получить или создать криптовалюту из API."""
        from .models import Cryptocurrency

        try:
            return Cryptocurrency.objects.get(coingecko_id=coingecko_id)
        except Cryptocurrency.DoesNotExist:
            pass

        info = cls.get_crypto_info(coingecko_id)
        if not info:
            return None

        price = Decimal("0")
        if "market_data" in info and "current_price" in info["market_data"]:
            usd_price = info["market_data"]["current_price"].get("usd")
            if usd_price:
                price = Decimal(str(usd_price))

        crypto = Cryptocurrency.objects.create(
            coingecko_id=coingecko_id,
            symbol=info.get("symbol", "").upper(),
            name=info.get("name", ""),
            current_price=price,
            image_url=info.get("image", {}).get("small", ""),
        )

        return crypto
