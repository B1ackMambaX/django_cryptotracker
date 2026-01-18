import logging
from datetime import timedelta
from decimal import Decimal

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class CoinGeckoService:
    """Сервис для работы с CoinGecko API."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_TIMEOUT = timedelta(seconds=60)
    REQUEST_TIMEOUT = 30

    _price_cache = {}
    _cache_time = None
    _last_error = None

    @classmethod
    def get_last_error(cls):
        """Получить последнюю ошибку API."""
        return cls._last_error

    @classmethod
    def clear_error(cls):
        """Очистить последнюю ошибку."""
        cls._last_error = None

    @classmethod
    def search_crypto(cls, query):
        """Поиск криптовалюты по названию или символу."""
        cls._last_error = None
        try:
            logger.info(f"CoinGecko API: Searching for '{query}'")
            response = requests.get(
                f"{cls.BASE_URL}/search", params={"query": query}, timeout=cls.REQUEST_TIMEOUT
            )
            logger.info(f"CoinGecko API: Search response status {response.status_code}")
            response.raise_for_status()
            data = response.json()
            results = data.get("coins", [])[:10]
            logger.info(f"CoinGecko API: Found {len(results)} results for '{query}'")
            return results
        except requests.Timeout:
            error_msg = "Превышено время ожидания ответа от CoinGecko API"
            logger.error(f"CoinGecko API: Timeout while searching for '{query}'")
            cls._last_error = error_msg
            return []
        except requests.ConnectionError:
            error_msg = "Не удалось подключиться к CoinGecko API"
            logger.error(f"CoinGecko API: Connection error while searching for '{query}'")
            cls._last_error = error_msg
            return []
        except requests.HTTPError as e:
            error_msg = f"Ошибка CoinGecko API: {e.response.status_code}"
            logger.error(f"CoinGecko API: HTTP error {e.response.status_code} while searching for '{query}'")
            cls._last_error = error_msg
            return []
        except requests.RequestException as e:
            error_msg = "Ошибка при запросе к CoinGecko API"
            logger.error(f"CoinGecko API: Request error while searching for '{query}': {e}")
            cls._last_error = error_msg
            return []

    @classmethod
    def get_crypto_info(cls, coingecko_id):
        """Получить информацию о криптовалюте по ID."""
        cls._last_error = None
        try:
            logger.info(f"CoinGecko API: Getting info for '{coingecko_id}'")
            response = requests.get(
                f"{cls.BASE_URL}/coins/{coingecko_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                },
                timeout=cls.REQUEST_TIMEOUT,
            )
            logger.info(f"CoinGecko API: Info response status {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            error_msg = "Превышено время ожидания ответа от CoinGecko API"
            logger.error(f"CoinGecko API: Timeout while getting info for '{coingecko_id}'")
            cls._last_error = error_msg
            return None
        except requests.ConnectionError:
            error_msg = "Не удалось подключиться к CoinGecko API"
            logger.error(f"CoinGecko API: Connection error while getting info for '{coingecko_id}'")
            cls._last_error = error_msg
            return None
        except requests.HTTPError as e:
            error_msg = f"Ошибка CoinGecko API: {e.response.status_code}"
            logger.error(f"CoinGecko API: HTTP error {e.response.status_code} while getting info for '{coingecko_id}'")
            cls._last_error = error_msg
            return None
        except requests.RequestException as e:
            error_msg = "Ошибка при запросе к CoinGecko API"
            logger.error(f"CoinGecko API: Request error while getting info for '{coingecko_id}': {e}")
            cls._last_error = error_msg
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
            logger.debug(f"CoinGecko API: Using cached price for '{coingecko_id}'")
            return cls._price_cache[coingecko_id]

        cls._last_error = None
        try:
            logger.info(f"CoinGecko API: Getting price for '{coingecko_id}'")
            response = requests.get(
                f"{cls.BASE_URL}/simple/price",
                params={"ids": coingecko_id, "vs_currencies": "usd"},
                timeout=cls.REQUEST_TIMEOUT,
            )
            logger.info(f"CoinGecko API: Price response status {response.status_code}")
            response.raise_for_status()
            data = response.json()

            if coingecko_id in data:
                price = Decimal(str(data[coingecko_id]["usd"]))
                cls._price_cache[coingecko_id] = price
                cls._cache_time = now
                logger.info(f"CoinGecko API: Price for '{coingecko_id}' is ${price}")
                return price
        except requests.Timeout:
            error_msg = "Превышено время ожидания ответа от CoinGecko API"
            logger.error(f"CoinGecko API: Timeout while getting price for '{coingecko_id}'")
            cls._last_error = error_msg
        except requests.ConnectionError:
            error_msg = "Не удалось подключиться к CoinGecko API"
            logger.error(f"CoinGecko API: Connection error while getting price for '{coingecko_id}'")
            cls._last_error = error_msg
        except requests.HTTPError as e:
            error_msg = f"Ошибка CoinGecko API: {e.response.status_code}"
            logger.error(f"CoinGecko API: HTTP error {e.response.status_code} while getting price for '{coingecko_id}'")
            cls._last_error = error_msg
        except (requests.RequestException, KeyError, ValueError) as e:
            error_msg = "Ошибка при запросе к CoinGecko API"
            logger.error(f"CoinGecko API: Error while getting price for '{coingecko_id}': {e}")
            cls._last_error = error_msg

        return None

    @classmethod
    def get_prices_bulk(cls, coingecko_ids):
        """Получить цены для нескольких криптовалют."""
        if not coingecko_ids:
            return {}

        cls._last_error = None
        try:
            ids_str = ",".join(coingecko_ids)
            logger.info(f"CoinGecko API: Getting bulk prices for {len(coingecko_ids)} coins")
            response = requests.get(
                f"{cls.BASE_URL}/simple/price",
                params={"ids": ids_str, "vs_currencies": "usd"},
                timeout=cls.REQUEST_TIMEOUT,
            )
            logger.info(f"CoinGecko API: Bulk price response status {response.status_code}")
            response.raise_for_status()
            data = response.json()

            prices = {}
            for coin_id, price_data in data.items():
                if "usd" in price_data:
                    prices[coin_id] = Decimal(str(price_data["usd"]))

            cls._price_cache.update(prices)
            cls._cache_time = timezone.now()
            logger.info(f"CoinGecko API: Got prices for {len(prices)} coins")

            return prices
        except requests.Timeout:
            error_msg = "Превышено время ожидания ответа от CoinGecko API"
            logger.error("CoinGecko API: Timeout while getting bulk prices")
            cls._last_error = error_msg
            return {}
        except requests.ConnectionError:
            error_msg = "Не удалось подключиться к CoinGecko API"
            logger.error("CoinGecko API: Connection error while getting bulk prices")
            cls._last_error = error_msg
            return {}
        except requests.HTTPError as e:
            error_msg = f"Ошибка CoinGecko API: {e.response.status_code}"
            logger.error(f"CoinGecko API: HTTP error {e.response.status_code} while getting bulk prices")
            cls._last_error = error_msg
            return {}
        except requests.RequestException as e:
            error_msg = "Ошибка при запросе к CoinGecko API"
            logger.error(f"CoinGecko API: Request error while getting bulk prices: {e}")
            cls._last_error = error_msg
            return {}

    @classmethod
    def update_cryptocurrency_prices(cls, cryptocurrencies):
        """Обновить цены для списка криптовалют в БД."""
        if not cryptocurrencies:
            return True

        coingecko_ids = [c.coingecko_id for c in cryptocurrencies]
        prices = cls.get_prices_bulk(coingecko_ids)

        if not prices and cls._last_error:
            return False

        for crypto in cryptocurrencies:
            if crypto.coingecko_id in prices:
                crypto.current_price = prices[crypto.coingecko_id]
                crypto.save(update_fields=["current_price", "last_updated"])

        return True

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
        logger.info(f"CoinGecko API: Created cryptocurrency '{crypto.name}' ({crypto.symbol})")

        return crypto
