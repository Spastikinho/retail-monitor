"""
Unit tests for connectors.
"""
import pytest

from apps.scraping.connectors.ozon import OzonConnector
from apps.scraping.connectors.vkusvill import VkusvillConnector
from apps.scraping.connectors.perekrestok import PerekrestokConnector
from apps.scraping.connectors.lavka import LavkaConnector


class TestOzonConnector:
    """Tests for OzonConnector."""

    def test_parse_product_id_standard_url(self):
        connector = OzonConnector()
        url = 'https://www.ozon.ru/product/kuraga-dzhambo-500g-123456789/'
        assert connector.parse_product_id(url) == '123456789'

    def test_parse_product_id_with_params(self):
        connector = OzonConnector()
        url = 'https://www.ozon.ru/product/some-product-987654321/?from=search'
        assert connector.parse_product_id(url) == '987654321'

    def test_parse_product_id_invalid_url(self):
        connector = OzonConnector()
        url = 'https://www.ozon.ru/category/123/'
        assert connector.parse_product_id(url) is None


class TestVkusvillConnector:
    """Tests for VkusvillConnector."""

    def test_parse_product_id_standard_url(self):
        connector = VkusvillConnector()
        url = 'https://vkusvill.ru/goods/kuraga-premium-12345.html'
        assert connector.parse_product_id(url) == '12345'

    def test_parse_product_id_invalid_url(self):
        connector = VkusvillConnector()
        url = 'https://vkusvill.ru/catalog/123/'
        assert connector.parse_product_id(url) is None


class TestPerekrestokConnector:
    """Tests for PerekrestokConnector."""

    def test_parse_product_id_standard_url(self):
        connector = PerekrestokConnector()
        url = 'https://www.perekrestok.ru/cat/456/p/kuraga-789012'
        assert connector.parse_product_id(url) == '789012'

    def test_parse_product_id_invalid_url(self):
        connector = PerekrestokConnector()
        url = 'https://www.perekrestok.ru/catalog/'
        assert connector.parse_product_id(url) is None


class TestLavkaConnector:
    """Tests for LavkaConnector."""

    def test_parse_product_id_standard_url(self):
        connector = LavkaConnector()
        url = 'https://lavka.yandex.ru/product/kuraga-abc123'
        assert connector.parse_product_id(url) == 'kuraga-abc123'

    def test_parse_product_id_invalid_url(self):
        connector = LavkaConnector()
        url = 'https://lavka.yandex.ru/favorites'
        assert connector.parse_product_id(url) is None
