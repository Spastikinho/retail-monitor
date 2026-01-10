"""
Unit tests for Ozon connector price parsing.
"""
import pytest
from decimal import Decimal

from apps.scraping.connectors.ozon import OzonConnector


class TestOzonPriceParsing:
    """Tests for OzonConnector._parse_ozon_prices()."""

    @pytest.fixture
    def connector(self):
        return OzonConnector()

    def test_parse_single_price(self, connector):
        """Test parsing single price."""
        result = connector._parse_ozon_prices('499 ₽')
        assert result['regular'] == Decimal('499')
        assert 'promo' not in result
        assert 'card' not in result

    def test_parse_price_with_spaces(self, connector):
        """Test parsing price with thousand separators."""
        result = connector._parse_ozon_prices('1 234 ₽')
        assert result['regular'] == Decimal('1234')

    def test_parse_promo_price(self, connector):
        """Test parsing regular and promo price."""
        price_text = '399 ₽\n599 ₽'
        result = connector._parse_ozon_prices(price_text)
        assert result['promo'] == Decimal('399')
        assert result['regular'] == Decimal('599')

    def test_parse_card_price(self, connector):
        """Test parsing with Ozon card price."""
        price_text = 'c Ozon Картой\n379 ₽\n399 ₽\n599 ₽'
        result = connector._parse_ozon_prices(price_text)
        assert result['card'] == Decimal('379')
        assert result['promo'] == Decimal('399')
        assert result['regular'] == Decimal('599')

    def test_parse_card_indicator_sets_lowest_as_card(self, connector):
        """Test that card indicator marks lowest price as card price."""
        price_text = '349 ₽ с картой\n599 ₽'
        result = connector._parse_ozon_prices(price_text)
        assert result['card'] == Decimal('349')

    def test_parse_empty_returns_empty_dict(self, connector):
        """Test parsing empty string."""
        result = connector._parse_ozon_prices('')
        assert result == {}

    def test_parse_no_prices_returns_empty_dict(self, connector):
        """Test parsing string without prices."""
        result = connector._parse_ozon_prices('Нет в наличии')
        assert result == {}

    def test_parse_complex_block(self, connector):
        """Test parsing complex Ozon price block."""
        price_text = '''
        Цена с Ozon Картой
        449 ₽

        Обычная цена
        499 ₽

        Без скидки
        699 ₽
        '''
        result = connector._parse_ozon_prices(price_text)
        # Should find three prices and assign them correctly
        assert result['card'] == Decimal('449')
        assert result['promo'] == Decimal('499')
        assert result['regular'] == Decimal('699')


class TestOzonProductIdParsing:
    """Tests for OzonConnector.parse_product_id()."""

    @pytest.fixture
    def connector(self):
        return OzonConnector()

    def test_parse_standard_url(self, connector):
        url = 'https://www.ozon.ru/product/kuraga-dzhambo-500g-123456789/'
        assert connector.parse_product_id(url) == '123456789'

    def test_parse_url_with_query(self, connector):
        url = 'https://www.ozon.ru/product/some-product-987654321/?from=search&tab=reviews'
        assert connector.parse_product_id(url) == '987654321'

    def test_parse_url_without_trailing_slash(self, connector):
        url = 'https://ozon.ru/product/test-product-555666777'
        assert connector.parse_product_id(url) == '555666777'

    def test_parse_short_url(self, connector):
        url = 'https://ozon.ru/product/123/'
        assert connector.parse_product_id(url) == '123'

    def test_parse_category_url_returns_none(self, connector):
        url = 'https://www.ozon.ru/category/suhofrukty-123456/'
        assert connector.parse_product_id(url) is None

    def test_parse_search_url_returns_none(self, connector):
        url = 'https://www.ozon.ru/search/?text=курага'
        assert connector.parse_product_id(url) is None

    def test_parse_empty_url_returns_none(self, connector):
        assert connector.parse_product_id('') is None

    def test_parse_different_domain_returns_none(self, connector):
        url = 'https://vkusvill.ru/goods/kuraga-12345.html'
        assert connector.parse_product_id(url) is None


class TestOzonConnectorAttributes:
    """Tests for OzonConnector class attributes."""

    def test_retailer_slug(self):
        assert OzonConnector.retailer_slug == 'ozon'

    def test_requires_auth_false(self):
        assert OzonConnector.requires_auth is False

    def test_selectors_defined(self):
        assert 'title' in OzonConnector.SELECTORS
        assert 'price_block' in OzonConnector.SELECTORS
        assert 'rating' in OzonConnector.SELECTORS
        assert 'reviews_count' in OzonConnector.SELECTORS
        assert 'in_stock' in OzonConnector.SELECTORS
        assert 'out_of_stock' in OzonConnector.SELECTORS
