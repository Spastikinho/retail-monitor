"""
Unit tests for Django models.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.utils import timezone

from apps.products.models import Product, Listing
from apps.retailers.models import Retailer
from apps.scraping.models import ScrapeSession, SnapshotPrice, SnapshotReview, ReviewItem
from apps.alerts.models import AlertRule, AlertEvent


@pytest.mark.django_db
class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self):
        product = Product.objects.create(
            name='Курага Джамбо',
            brand='TestBrand',
            is_own=True,
            weight_grams=500
        )
        assert product.pk is not None
        assert str(product) == 'TestBrand - Курага Джамбо 500г'

    def test_create_product_without_weight(self):
        product = Product.objects.create(
            name='Чернослив',
            brand='TestBrand',
            is_own=False
        )
        assert str(product) == 'TestBrand - Чернослив'

    def test_active_listings_count(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Test Retailer',
            slug='test',
            base_url='https://test.com',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )

        # Create active listing
        Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://test.com/1',
            is_active=True
        )
        # Create inactive listing
        retailer2 = Retailer.objects.create(
            name='Test Retailer 2',
            slug='test2',
            base_url='https://test2.com',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        Listing.objects.create(
            product=product,
            retailer=retailer2,
            external_url='https://test2.com/1',
            is_active=False
        )

        assert product.active_listings_count == 1


@pytest.mark.django_db
class TestListingModel:
    """Tests for Listing model."""

    def test_create_listing(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123',
            external_id='123'
        )
        assert str(listing) == 'Test @ Ozon'

    def test_listing_unique_per_retailer(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        with pytest.raises(Exception):  # IntegrityError
            Listing.objects.create(
                product=product,
                retailer=retailer,
                external_url='https://ozon.ru/product/456'
            )


@pytest.mark.django_db
class TestRetailerModel:
    """Tests for Retailer model."""

    def test_create_retailer(self):
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector',
            is_active=True,
            rate_limit_rpm=10
        )
        assert str(retailer) == 'Ozon'
        assert retailer.default_region == 'moscow'


@pytest.mark.django_db
class TestScrapeSessionModel:
    """Tests for ScrapeSession model."""

    def test_create_session(self):
        session = ScrapeSession.objects.create(
            status='pending',
            trigger_type='manual'
        )
        assert session.pk is not None
        assert session.listings_total == 0
        assert session.listings_success == 0
        assert session.listings_failed == 0

    def test_session_duration(self):
        now = timezone.now()
        session = ScrapeSession.objects.create(
            status='completed',
            started_at=now - timedelta(minutes=5),
            finished_at=now
        )
        assert session.duration.total_seconds() == 300

    def test_session_duration_none_if_not_finished(self):
        session = ScrapeSession.objects.create(
            status='running',
            started_at=timezone.now()
        )
        assert session.duration is None


@pytest.mark.django_db
class TestSnapshotPriceModel:
    """Tests for SnapshotPrice model."""

    def test_create_snapshot(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        snapshot = SnapshotPrice.objects.create(
            listing=listing,
            period_month=date(2024, 1, 1),
            price_regular=Decimal('299.99'),
            price_promo=Decimal('249.99'),
            price_final=Decimal('249.99'),
            in_stock=True,
            rating_avg=Decimal('4.5'),
            reviews_count=100
        )
        assert snapshot.currency == 'RUB'
        assert snapshot.price_final == Decimal('249.99')


@pytest.mark.django_db
class TestSnapshotReviewModel:
    """Tests for SnapshotReview model."""

    def test_auto_calculate_negative_reviews(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        snapshot = SnapshotReview.objects.create(
            listing=listing,
            period_month=date(2024, 1, 1),
            reviews_1_count=5,
            reviews_2_count=3,
            reviews_3_count=2,
            reviews_4_count=10,
            reviews_5_count=80
        )
        assert snapshot.reviews_1_3_count == 10


@pytest.mark.django_db
class TestReviewItemModel:
    """Tests for ReviewItem model."""

    def test_auto_sentiment_negative(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        review = ReviewItem.objects.create(
            listing=listing,
            external_id='rev123',
            rating=2,
            text='Плохой товар'
        )
        assert review.sentiment == 'negative'

    def test_auto_sentiment_neutral(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        review = ReviewItem.objects.create(
            listing=listing,
            external_id='rev456',
            rating=4,
            text='Нормальный товар'
        )
        assert review.sentiment == 'neutral'

    def test_auto_sentiment_positive(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )

        review = ReviewItem.objects.create(
            listing=listing,
            external_id='rev789',
            rating=5,
            text='Отличный товар!'
        )
        assert review.sentiment == 'positive'


@pytest.mark.django_db
class TestAlertRuleModel:
    """Tests for AlertRule model."""

    def test_create_alert_rule(self):
        rule = AlertRule.objects.create(
            name='Price Alert',
            alert_type='price_increase',
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123456789'],
            cooldown_hours=24
        )
        assert str(rule) == 'Price Alert'
        assert rule.is_active is True

    def test_alert_rule_with_product_scope(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        rule = AlertRule.objects.create(
            name='Product Alert',
            alert_type='new_negative_review',
            product=product,
            threshold_rating=3,
            channel='telegram',
            recipients=['123456789']
        )
        assert rule.product == product
        assert rule.retailer is None


@pytest.mark.django_db
class TestAlertEventModel:
    """Tests for AlertEvent model."""

    def test_create_alert_event(self):
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )
        rule = AlertRule.objects.create(
            name='Test Rule',
            alert_type='price_increase',
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123456789']
        )

        event = AlertEvent.objects.create(
            alert_rule=rule,
            listing=listing,
            message='Price increased by 10%',
            details={'old_price': 100, 'new_price': 110, 'pct_change': 10}
        )
        assert event.is_delivered is False
        assert event.delivered_at is None
        assert 'old_price' in event.details
