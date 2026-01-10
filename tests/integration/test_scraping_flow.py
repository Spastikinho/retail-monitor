"""
Integration tests for the end-to-end scraping flow.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from apps.products.models import Product, Listing
from apps.retailers.models import Retailer
from apps.scraping.models import ScrapeSession, SnapshotPrice
from apps.scraping.connectors.base import ScrapeResult, PriceData
from apps.scraping.tasks import scrape_listing_async, get_connector_class


@pytest.fixture
def retailer(db):
    """Create a test retailer."""
    return Retailer.objects.create(
        name='Test Ozon',
        slug='ozon',
        connector_class='apps.scraping.connectors.ozon.OzonConnector',
        base_url='https://ozon.ru',
        is_active=True,
    )


@pytest.fixture
def product(db):
    """Create a test product."""
    return Product.objects.create(
        name='Test Kuraga',
        brand='Test Brand',
        is_own=True,
    )


@pytest.fixture
def listing(db, product, retailer):
    """Create a test listing."""
    return Listing.objects.create(
        product=product,
        retailer=retailer,
        external_url='https://ozon.ru/product/test-kuraga-123456/',
        is_active=True,
    )


@pytest.fixture
def scrape_session(db, retailer):
    """Create a test scrape session."""
    return ScrapeSession.objects.create(
        retailer=retailer,
        status=ScrapeSession.StatusChoices.PENDING,
        trigger_type=ScrapeSession.TriggerChoices.MANUAL,
    )


class TestGetConnectorClass:
    """Tests for dynamic connector loading."""

    def test_load_ozon_connector(self):
        connector_class = get_connector_class('apps.scraping.connectors.ozon.OzonConnector')
        from apps.scraping.connectors.ozon import OzonConnector
        assert connector_class == OzonConnector

    def test_load_invalid_path(self):
        with pytest.raises(ModuleNotFoundError):
            get_connector_class('apps.scraping.connectors.invalid.InvalidConnector')


@pytest.mark.django_db
class TestScrapeListingAsync:
    """Tests for async scraping function."""

    @pytest.mark.asyncio
    async def test_successful_scrape_creates_snapshot(self, listing, scrape_session):
        """Test that successful scrape creates a SnapshotPrice record."""
        # Mock the scrape result
        mock_result = ScrapeResult(
            success=True,
            price_data=PriceData(
                price_regular=Decimal('599'),
                price_promo=Decimal('399'),
                price_final=Decimal('399'),
                in_stock=True,
                rating_avg=4.7,
                reviews_count=1234,
            ),
            raw_data={'test': 'data'},
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, scrape_session)

        assert result['success'] is True
        assert result['price_final'] == 399.0
        assert result['rating'] == 4.7
        assert 'snapshot_id' in result

        # Verify snapshot was created
        snapshot = SnapshotPrice.objects.get(pk=result['snapshot_id'])
        assert snapshot.listing == listing
        assert snapshot.session == scrape_session
        assert snapshot.price_regular == Decimal('599')
        assert snapshot.price_promo == Decimal('399')
        assert snapshot.price_final == Decimal('399')
        assert snapshot.in_stock is True
        assert snapshot.rating_avg == 4.7
        assert snapshot.reviews_count == 1234

    @pytest.mark.asyncio
    async def test_failed_scrape_returns_error(self, listing, scrape_session):
        """Test that failed scrape returns error info."""
        mock_result = ScrapeResult(
            success=False,
            error_message='Page not found',
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, scrape_session)

        assert result['success'] is False
        assert result['error'] == 'Page not found'

        # Verify no snapshot was created
        assert SnapshotPrice.objects.filter(listing=listing).count() == 0


@pytest.mark.django_db
class TestPriceDataFlow:
    """Tests for price data normalization in the full flow."""

    @pytest.mark.asyncio
    async def test_single_price_normalized(self, listing, scrape_session):
        """Test that single price is properly normalized."""
        mock_result = ScrapeResult(
            success=True,
            price_data=PriceData(
                price_regular=Decimal('499'),
                price_final=Decimal('499'),
                in_stock=True,
            ),
            raw_data={},
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, scrape_session)

        snapshot = SnapshotPrice.objects.get(pk=result['snapshot_id'])
        assert snapshot.price_regular == Decimal('499')
        assert snapshot.price_promo is None
        assert snapshot.price_card is None
        assert snapshot.price_final == Decimal('499')

    @pytest.mark.asyncio
    async def test_card_price_is_final(self, listing, scrape_session):
        """Test that card price becomes final when it's the lowest."""
        mock_result = ScrapeResult(
            success=True,
            price_data=PriceData(
                price_regular=Decimal('599'),
                price_promo=Decimal('499'),
                price_card=Decimal('449'),
                price_final=Decimal('449'),
                in_stock=True,
            ),
            raw_data={},
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, scrape_session)

        snapshot = SnapshotPrice.objects.get(pk=result['snapshot_id'])
        assert snapshot.price_card == Decimal('449')
        assert snapshot.price_final == Decimal('449')


@pytest.mark.django_db
class TestSessionTracking:
    """Tests for session tracking during scraping."""

    @pytest.mark.asyncio
    async def test_snapshot_linked_to_session(self, listing, scrape_session):
        """Test that snapshot is linked to the scrape session."""
        mock_result = ScrapeResult(
            success=True,
            price_data=PriceData(
                price_regular=Decimal('499'),
                price_final=Decimal('499'),
                in_stock=True,
            ),
            raw_data={},
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, scrape_session)

        snapshot = SnapshotPrice.objects.get(pk=result['snapshot_id'])
        assert snapshot.session == scrape_session
        assert snapshot.period_month == date.today().replace(day=1)

    @pytest.mark.asyncio
    async def test_scrape_without_session(self, listing):
        """Test scraping works without an explicit session."""
        mock_result = ScrapeResult(
            success=True,
            price_data=PriceData(
                price_regular=Decimal('499'),
                price_final=Decimal('499'),
                in_stock=True,
            ),
            raw_data={},
        )

        with patch('apps.scraping.tasks.BrowserManager') as mock_browser:
            mock_browser_instance = MagicMock()
            mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
            mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('apps.scraping.tasks.get_connector_class') as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.return_value.scrape_product = AsyncMock(return_value=mock_result)
                mock_get_connector.return_value = mock_connector

                result = await scrape_listing_async(listing, session=None)

        assert result['success'] is True
        snapshot = SnapshotPrice.objects.get(pk=result['snapshot_id'])
        assert snapshot.session is None
