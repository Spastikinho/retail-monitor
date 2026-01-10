"""
Unit tests for Perekrestok connector.
"""
import pytest

from apps.scraping.connectors.perekrestok import PerekrestokConnector


class TestPerekrestokProductIdParsing:
    """Tests for PerekrestokConnector.parse_product_id()."""

    @pytest.fixture
    def connector(self):
        return PerekrestokConnector()

    def test_parse_standard_url(self, connector):
        url = 'https://www.perekrestok.ru/cat/456/p/kuraga-789012'
        assert connector.parse_product_id(url) == '789012'

    def test_parse_url_with_long_product_name(self, connector):
        url = 'https://www.perekrestok.ru/cat/123/p/kuraga-premium-500g-extra-quality-456789'
        assert connector.parse_product_id(url) == '456789'

    def test_parse_url_with_query_params(self, connector):
        url = 'https://www.perekrestok.ru/cat/100/p/product-name-123456?some=param'
        assert connector.parse_product_id(url) == '123456'

    def test_parse_url_different_category(self, connector):
        url = 'https://perekrestok.ru/cat/999/p/chernosliv-organic-555'
        assert connector.parse_product_id(url) == '555'

    def test_parse_category_url_returns_none(self, connector):
        url = 'https://www.perekrestok.ru/cat/456/suhofrukty'
        assert connector.parse_product_id(url) is None

    def test_parse_main_page_returns_none(self, connector):
        url = 'https://www.perekrestok.ru/'
        assert connector.parse_product_id(url) is None

    def test_parse_search_url_returns_none(self, connector):
        url = 'https://www.perekrestok.ru/search?q=курага'
        assert connector.parse_product_id(url) is None

    def test_parse_empty_url_returns_none(self, connector):
        assert connector.parse_product_id('') is None

    def test_parse_different_domain_returns_none(self, connector):
        url = 'https://vkusvill.ru/goods/kuraga-12345.html'
        assert connector.parse_product_id(url) is None


class TestPerekrestokConnectorAttributes:
    """Tests for PerekrestokConnector class attributes."""

    def test_retailer_slug(self):
        assert PerekrestokConnector.retailer_slug == 'perekrestok'

    def test_requires_auth_false(self):
        assert PerekrestokConnector.requires_auth is False

    def test_product_url_pattern_defined(self):
        assert PerekrestokConnector.PRODUCT_URL_PATTERN is not None

    def test_selectors_defined(self):
        assert 'title' in PerekrestokConnector.SELECTORS
        assert 'price_current' in PerekrestokConnector.SELECTORS
        assert 'price_old' in PerekrestokConnector.SELECTORS
        assert 'rating' in PerekrestokConnector.SELECTORS
        assert 'reviews_count' in PerekrestokConnector.SELECTORS
        assert 'in_stock' in PerekrestokConnector.SELECTORS
        assert 'out_of_stock' in PerekrestokConnector.SELECTORS
        assert 'reviews_container' in PerekrestokConnector.SELECTORS
        assert 'review_item' in PerekrestokConnector.SELECTORS
