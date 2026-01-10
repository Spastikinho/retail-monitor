"""
Unit tests for Yandex Lavka connector.
"""
import pytest

from apps.scraping.connectors.lavka import LavkaConnector


class TestLavkaProductIdParsing:
    """Tests for LavkaConnector.parse_product_id()."""

    @pytest.fixture
    def connector(self):
        return LavkaConnector()

    def test_parse_standard_url(self, connector):
        url = 'https://lavka.yandex.ru/213/good/kuraga-premium'
        assert connector.parse_product_id(url) == 'kuraga-premium'

    def test_parse_url_with_underscores(self, connector):
        url = 'https://lavka.yandex.ru/213/good/dried_apricots_500g'
        assert connector.parse_product_id(url) == 'dried_apricots_500g'

    def test_parse_url_with_numbers(self, connector):
        url = 'https://lavka.yandex.ru/213/good/product123'
        assert connector.parse_product_id(url) == 'product123'

    def test_parse_url_alphanumeric_slug(self, connector):
        url = 'https://lavka.yandex.ru/10719/good/abc123-xyz789'
        assert connector.parse_product_id(url) == 'abc123-xyz789'

    def test_parse_url_different_region_code(self, connector):
        url = 'https://lavka.yandex.ru/10719/good/some-product'
        assert connector.parse_product_id(url) == 'some-product'

    def test_parse_main_page_returns_none(self, connector):
        url = 'https://lavka.yandex.ru/'
        assert connector.parse_product_id(url) is None

    def test_parse_favorites_url_returns_none(self, connector):
        url = 'https://lavka.yandex.ru/favorites'
        assert connector.parse_product_id(url) is None

    def test_parse_cart_url_returns_none(self, connector):
        url = 'https://lavka.yandex.ru/cart'
        assert connector.parse_product_id(url) is None

    def test_parse_category_url_returns_none(self, connector):
        url = 'https://lavka.yandex.ru/213/category/fruits'
        assert connector.parse_product_id(url) is None

    def test_parse_empty_url_returns_none(self, connector):
        assert connector.parse_product_id('') is None

    def test_parse_different_domain_returns_none(self, connector):
        url = 'https://ozon.ru/product/123456/'
        assert connector.parse_product_id(url) is None


class TestLavkaConnectorAttributes:
    """Tests for LavkaConnector class attributes."""

    def test_retailer_slug(self):
        assert LavkaConnector.retailer_slug == 'lavka'

    def test_requires_auth_false(self):
        assert LavkaConnector.requires_auth is False

    def test_product_url_pattern_defined(self):
        assert LavkaConnector.PRODUCT_URL_PATTERN is not None

    def test_selectors_defined(self):
        assert 'title' in LavkaConnector.SELECTORS
        assert 'price_current' in LavkaConnector.SELECTORS
        assert 'price_old' in LavkaConnector.SELECTORS
        assert 'rating' in LavkaConnector.SELECTORS
        assert 'reviews_count' in LavkaConnector.SELECTORS
        assert 'in_stock' in LavkaConnector.SELECTORS
        assert 'out_of_stock' in LavkaConnector.SELECTORS
        assert 'reviews_container' in LavkaConnector.SELECTORS
        assert 'review_item' in LavkaConnector.SELECTORS
