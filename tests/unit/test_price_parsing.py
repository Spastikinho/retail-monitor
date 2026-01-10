"""
Unit tests for price parsing and normalization.
"""
from decimal import Decimal
import pytest

from apps.scraping.connectors.base import BaseConnector


class TestPriceParsing:
    """Tests for BaseConnector.parse_price()."""

    def test_parse_simple_price(self):
        assert BaseConnector.parse_price('499 ₽') == Decimal('499')

    def test_parse_price_with_spaces(self):
        assert BaseConnector.parse_price('1 234 ₽') == Decimal('1234')

    def test_parse_price_with_comma(self):
        assert BaseConnector.parse_price('499,50 ₽') == Decimal('499.50')

    def test_parse_price_rub(self):
        assert BaseConnector.parse_price('499 руб.') == Decimal('499')

    def test_parse_price_without_symbol(self):
        assert BaseConnector.parse_price('499') == Decimal('499')

    def test_parse_empty_string(self):
        assert BaseConnector.parse_price('') is None

    def test_parse_none(self):
        assert BaseConnector.parse_price(None) is None

    def test_parse_invalid_string(self):
        assert BaseConnector.parse_price('нет в наличии') is None


class TestRatingParsing:
    """Tests for BaseConnector.parse_rating()."""

    def test_parse_simple_rating(self):
        assert BaseConnector.parse_rating('4.7') == 4.7

    def test_parse_rating_with_comma(self):
        assert BaseConnector.parse_rating('4,7') == 4.7

    def test_parse_rating_with_context(self):
        assert BaseConnector.parse_rating('4.7 из 5') == 4.7

    def test_parse_integer_rating(self):
        assert BaseConnector.parse_rating('5') == 5.0

    def test_parse_rating_out_of_range(self):
        assert BaseConnector.parse_rating('10.5') is None

    def test_parse_empty_rating(self):
        assert BaseConnector.parse_rating('') is None


class TestReviewsCountParsing:
    """Tests for BaseConnector.parse_reviews_count()."""

    def test_parse_simple_count(self):
        assert BaseConnector.parse_reviews_count('1234') == 1234

    def test_parse_count_with_text(self):
        assert BaseConnector.parse_reviews_count('1234 отзыва') == 1234

    def test_parse_count_with_spaces(self):
        assert BaseConnector.parse_reviews_count('1 234 отзывов') == 1234

    def test_parse_empty_count(self):
        assert BaseConnector.parse_reviews_count('') is None


class TestPriceNormalization:
    """Tests for price normalization logic."""

    def test_single_price_becomes_regular(self):
        # Create a concrete implementation for testing
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        result = connector.normalize_price({'current': Decimal('499')})

        assert result.price_regular == Decimal('499')
        assert result.price_final == Decimal('499')
        assert result.price_promo is None

    def test_promo_price_lower_than_regular(self):
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        result = connector.normalize_price({
            'regular': Decimal('599'),
            'promo': Decimal('399'),
        })

        assert result.price_regular == Decimal('599')
        assert result.price_promo == Decimal('399')
        assert result.price_final == Decimal('399')

    def test_card_price_lowest(self):
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        result = connector.normalize_price({
            'regular': Decimal('599'),
            'promo': Decimal('499'),
            'card': Decimal('449'),
        })

        assert result.price_final == Decimal('449')


class TestReviewCategorization:
    """Tests for review categorization."""

    def test_rating_1_is_negative(self):
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        assert connector.categorize_review(1) == 'negative'
        assert connector.categorize_review(2) == 'negative'
        assert connector.categorize_review(3) == 'negative'

    def test_rating_4_is_neutral(self):
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        assert connector.categorize_review(4) == 'neutral'

    def test_rating_5_is_positive(self):
        class TestConnector(BaseConnector):
            async def scrape_product(self, url, browser=None):
                pass
            def parse_product_id(self, url):
                pass

        connector = TestConnector()
        assert connector.categorize_review(5) == 'positive'
