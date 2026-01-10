"""
Base connector class for all retailer integrations.
"""
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Normalized price data from scraping."""
    price_regular: Optional[Decimal] = None
    price_promo: Optional[Decimal] = None
    price_card: Optional[Decimal] = None
    price_final: Optional[Decimal] = None
    currency: str = 'RUB'
    in_stock: bool = True
    stock_quantity: Optional[int] = None
    rating_avg: Optional[float] = None
    reviews_count: Optional[int] = None
    title: str = ''


@dataclass
class ReviewData:
    """Single review data from scraping."""
    external_id: str
    rating: int
    text: str
    author_name: str = ''
    pros: str = ''
    cons: str = ''
    published_at: Optional[datetime] = None
    raw_data: dict = field(default_factory=dict)


@dataclass
class ScrapeResult:
    """Complete result from scraping a listing."""
    success: bool
    price_data: Optional[PriceData] = None
    reviews: list[ReviewData] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    error_message: str = ''
    scraped_at: datetime = field(default_factory=datetime.now)


class BaseConnector(ABC):
    """
    Abstract base class for retailer connectors.
    Each retailer implements its own connector with specific parsing logic.
    """

    retailer_slug: str = ''
    requires_auth: bool = False

    def __init__(self, session_data: Optional[dict] = None):
        """
        Initialize connector.

        Args:
            session_data: Optional dict with cookies/localStorage for auth
        """
        self.session_data = session_data or {}
        self.cookies = session_data.get('cookies', []) if session_data else []
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')

    @abstractmethod
    async def scrape_product(self, url: str, browser_manager=None) -> ScrapeResult:
        """
        Scrape product data from URL.

        Args:
            url: Product page URL
            browser_manager: Optional BrowserManager instance

        Returns:
            ScrapeResult with price and review data
        """
        pass

    @abstractmethod
    def parse_product_id(self, url: str) -> Optional[str]:
        """
        Extract product ID from URL.

        Args:
            url: Product page URL

        Returns:
            Product ID or None if not found
        """
        pass

    @staticmethod
    def parse_price(price_str: str) -> Optional[Decimal]:
        """
        Parse price string to Decimal.
        Handles various formats: "1 234,56 ₽", "1234.56", "1 234 руб."

        Args:
            price_str: Raw price string

        Returns:
            Decimal price or None if parsing failed
        """
        if not price_str:
            return None

        try:
            # Remove currency symbols and extra spaces
            cleaned = re.sub(r'[₽руб.р\s]', '', price_str)
            # Replace comma with dot for decimal
            cleaned = cleaned.replace(',', '.')
            # Remove any remaining non-numeric except dot
            cleaned = re.sub(r'[^\d.]', '', cleaned)

            if cleaned:
                return Decimal(cleaned)
        except Exception:
            pass

        return None

    @staticmethod
    def parse_rating(rating_str: str) -> Optional[float]:
        """
        Parse rating string to float.

        Args:
            rating_str: Raw rating string like "4.7" or "4,7 из 5"

        Returns:
            Float rating or None
        """
        if not rating_str:
            return None

        try:
            # Extract first number with optional decimal
            match = re.search(r'(\d+[.,]?\d*)', rating_str)
            if match:
                value = match.group(1).replace(',', '.')
                rating = float(value)
                # Validate rating is in expected range
                if 0 <= rating <= 5:
                    return round(rating, 1)
        except Exception:
            pass

        return None

    @staticmethod
    def parse_reviews_count(count_str: str) -> Optional[int]:
        """
        Parse reviews count string to int.

        Args:
            count_str: Raw string like "1 234 отзыва" or "1234"

        Returns:
            Integer count or None
        """
        if not count_str:
            return None

        try:
            # Remove non-digits
            cleaned = re.sub(r'\D', '', count_str)
            if cleaned:
                return int(cleaned)
        except Exception:
            pass

        return None

    def normalize_price(self, raw_prices: dict) -> PriceData:
        """
        Convert raw price data to normalized format.

        Args:
            raw_prices: Dict with price values from page

        Returns:
            PriceData with normalized values
        """
        regular = raw_prices.get('regular') or raw_prices.get('original')
        promo = raw_prices.get('promo') or raw_prices.get('discount')
        card = raw_prices.get('card')
        current = raw_prices.get('current') or raw_prices.get('price')

        # Convert to Decimal if strings
        if isinstance(regular, str):
            regular = self.parse_price(regular)
        if isinstance(promo, str):
            promo = self.parse_price(promo)
        if isinstance(card, str):
            card = self.parse_price(card)
        if isinstance(current, str):
            current = self.parse_price(current)

        # Determine final price
        prices = [p for p in [regular, promo, card, current] if p is not None]
        final = min(prices) if prices else None

        # If only current price exists, treat as regular
        if current and not regular and not promo:
            regular = current

        return PriceData(
            price_regular=regular,
            price_promo=promo,
            price_card=card,
            price_final=final,
            in_stock=raw_prices.get('in_stock', True),
            rating_avg=raw_prices.get('rating'),
            reviews_count=raw_prices.get('reviews_count'),
            title=raw_prices.get('title', ''),
        )

    def categorize_review(self, rating: int) -> str:
        """Categorize review by rating."""
        if rating <= 3:
            return 'negative'
        elif rating == 4:
            return 'neutral'
        else:
            return 'positive'
