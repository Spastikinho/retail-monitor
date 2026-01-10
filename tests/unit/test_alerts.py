"""
Unit tests for the alerts system.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.utils import timezone

from apps.products.models import Product, Listing
from apps.retailers.models import Retailer
from apps.scraping.models import SnapshotPrice, ReviewItem
from apps.alerts.models import AlertRule, AlertEvent


@pytest.mark.django_db
class TestAlertRuleMatching:
    """Tests for alert rule matching logic."""

    @pytest.fixture
    def setup_data(self):
        """Create test data for alerts."""
        # Create retailer
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )

        # Create products
        own_product = Product.objects.create(
            name='Own Product',
            brand='OwnBrand',
            is_own=True
        )
        competitor_product = Product.objects.create(
            name='Competitor Product',
            brand='CompBrand',
            is_own=False
        )

        # Create listings
        own_listing = Listing.objects.create(
            product=own_product,
            retailer=retailer,
            external_url='https://ozon.ru/product/own-123'
        )
        comp_listing = Listing.objects.create(
            product=competitor_product,
            retailer=retailer,
            external_url='https://ozon.ru/product/comp-456'
        )

        return {
            'retailer': retailer,
            'own_product': own_product,
            'competitor_product': competitor_product,
            'own_listing': own_listing,
            'comp_listing': comp_listing,
        }

    def test_price_increase_rule_matches(self, setup_data):
        """Test that price increase rule is matched correctly."""
        from apps.alerts.tasks import _get_matching_rules

        AlertRule.objects.create(
            name='Price Increase Alert',
            alert_type='price_increase',
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123'],
            is_active=True
        )

        rules = _get_matching_rules(
            'price_increase',
            setup_data['own_product'],
            setup_data['retailer']
        )

        assert rules.count() == 1
        assert rules.first().name == 'Price Increase Alert'

    def test_inactive_rule_not_matched(self, setup_data):
        """Test that inactive rules are not matched."""
        from apps.alerts.tasks import _get_matching_rules

        AlertRule.objects.create(
            name='Inactive Rule',
            alert_type='price_increase',
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123'],
            is_active=False
        )

        rules = _get_matching_rules(
            'price_increase',
            setup_data['own_product'],
            setup_data['retailer']
        )

        assert rules.count() == 0

    def test_product_specific_rule_matches(self, setup_data):
        """Test that product-specific rule matches only that product."""
        from apps.alerts.tasks import _get_matching_rules

        AlertRule.objects.create(
            name='Own Product Alert',
            alert_type='price_increase',
            product=setup_data['own_product'],
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123'],
            is_active=True
        )

        # Should match for own_product
        rules_own = _get_matching_rules(
            'price_increase',
            setup_data['own_product'],
            setup_data['retailer']
        )
        assert rules_own.count() == 1

        # Should not match for competitor_product
        rules_comp = _get_matching_rules(
            'price_increase',
            setup_data['competitor_product'],
            setup_data['retailer']
        )
        assert rules_comp.count() == 0


@pytest.mark.django_db
class TestCooldownLogic:
    """Tests for alert cooldown logic."""

    @pytest.fixture
    def setup_with_rule(self):
        """Create test data with an alert rule."""
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        product = Product.objects.create(
            name='Test Product',
            brand='Brand',
            is_own=True
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
            recipients=['123'],
            cooldown_hours=24,
            is_active=True
        )
        return {
            'retailer': retailer,
            'product': product,
            'listing': listing,
            'rule': rule,
        }

    def test_should_trigger_no_previous_event(self, setup_with_rule):
        """Test that rule should trigger when no previous event."""
        from apps.alerts.tasks import _should_trigger

        result = _should_trigger(
            setup_with_rule['rule'],
            setup_with_rule['listing']
        )
        assert result is True

    def test_should_not_trigger_within_cooldown(self, setup_with_rule):
        """Test that rule should not trigger within cooldown period."""
        from apps.alerts.tasks import _should_trigger

        # Create a recent event
        AlertEvent.objects.create(
            alert_rule=setup_with_rule['rule'],
            listing=setup_with_rule['listing'],
            message='Previous event',
            details={},
        )

        result = _should_trigger(
            setup_with_rule['rule'],
            setup_with_rule['listing']
        )
        assert result is False

    def test_should_trigger_after_cooldown(self, setup_with_rule):
        """Test that rule should trigger after cooldown period."""
        from apps.alerts.tasks import _should_trigger

        # Create an old event (manually set triggered_at)
        old_event = AlertEvent.objects.create(
            alert_rule=setup_with_rule['rule'],
            listing=setup_with_rule['listing'],
            message='Old event',
            details={},
        )
        # Backdate the event
        AlertEvent.objects.filter(pk=old_event.pk).update(
            triggered_at=timezone.now() - timedelta(hours=25)
        )

        result = _should_trigger(
            setup_with_rule['rule'],
            setup_with_rule['listing']
        )
        assert result is True

    def test_zero_cooldown_always_triggers(self, setup_with_rule):
        """Test that rule with zero cooldown always triggers."""
        from apps.alerts.tasks import _should_trigger

        # Update rule to have zero cooldown
        setup_with_rule['rule'].cooldown_hours = 0
        setup_with_rule['rule'].save()

        # Create a recent event
        AlertEvent.objects.create(
            alert_rule=setup_with_rule['rule'],
            listing=setup_with_rule['listing'],
            message='Recent event',
            details={},
        )

        result = _should_trigger(
            setup_with_rule['rule'],
            setup_with_rule['listing']
        )
        assert result is True


@pytest.mark.django_db
class TestAlertEventCreation:
    """Tests for alert event creation."""

    @pytest.fixture
    def setup_data(self):
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        product = Product.objects.create(
            name='Test Product',
            brand='Brand',
            is_own=True
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
            recipients=['123'],
            is_active=True
        )
        return {
            'retailer': retailer,
            'product': product,
            'listing': listing,
            'rule': rule,
        }

    @patch('apps.alerts.tasks.deliver_alert_event.delay')
    def test_create_alert_event(self, mock_deliver, setup_data):
        """Test that alert event is created and queued for delivery."""
        from apps.alerts.tasks import _create_alert_event

        event = _create_alert_event(
            rule=setup_data['rule'],
            listing=setup_data['listing'],
            snapshot=None,
            message='Test alert',
            details={'test': 'data'},
        )

        assert event.pk is not None
        assert event.alert_rule == setup_data['rule']
        assert event.listing == setup_data['listing']
        assert event.message == 'Test alert'
        assert event.details == {'test': 'data'}
        assert event.is_delivered is False

        # Check that delivery was queued
        mock_deliver.assert_called_once_with(str(event.pk))


@pytest.mark.django_db
class TestPriceAlertChecking:
    """Tests for price alert checking."""

    @pytest.fixture
    def setup_price_data(self):
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        product = Product.objects.create(
            name='Test Product',
            brand='Brand',
            is_own=True
        )
        listing = Listing.objects.create(
            product=product,
            retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )
        rule = AlertRule.objects.create(
            name='Price Increase 5%',
            alert_type='price_increase',
            threshold_pct=Decimal('5.00'),
            channel='telegram',
            recipients=['123'],
            is_active=True
        )

        # Create previous snapshot
        old_snapshot = SnapshotPrice.objects.create(
            listing=listing,
            period_month=date(2024, 1, 1),
            price_regular=Decimal('100.00'),
            price_final=Decimal('100.00'),
            in_stock=True,
        )

        return {
            'retailer': retailer,
            'product': product,
            'listing': listing,
            'rule': rule,
            'old_snapshot': old_snapshot,
        }

    @patch('apps.alerts.tasks.deliver_alert_event.delay')
    def test_price_increase_triggers_alert(self, mock_deliver, setup_price_data):
        """Test that price increase above threshold triggers alert."""
        from apps.alerts.tasks import check_price_alerts

        # Create new snapshot with price increase
        new_snapshot = SnapshotPrice.objects.create(
            listing=setup_price_data['listing'],
            period_month=date(2024, 1, 1),
            price_regular=Decimal('110.00'),
            price_final=Decimal('110.00'),
            in_stock=True,
        )

        result = check_price_alerts(str(new_snapshot.pk))

        assert result['success'] is True
        assert result['events_created'] == 1
        mock_deliver.assert_called_once()

    @patch('apps.alerts.tasks.deliver_alert_event.delay')
    def test_small_price_increase_no_alert(self, mock_deliver, setup_price_data):
        """Test that small price increase does not trigger alert."""
        from apps.alerts.tasks import check_price_alerts

        # Create new snapshot with small price increase (3%)
        new_snapshot = SnapshotPrice.objects.create(
            listing=setup_price_data['listing'],
            period_month=date(2024, 1, 1),
            price_regular=Decimal('103.00'),
            price_final=Decimal('103.00'),
            in_stock=True,
        )

        result = check_price_alerts(str(new_snapshot.pk))

        assert result['success'] is True
        assert result['events_created'] == 0
        mock_deliver.assert_not_called()


@pytest.mark.django_db
class TestReviewAlertChecking:
    """Tests for review alert checking."""

    @pytest.fixture
    def setup_review_data(self):
        retailer = Retailer.objects.create(
            name='Ozon',
            slug='ozon',
            base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        own_product = Product.objects.create(
            name='Own Product',
            brand='Brand',
            is_own=True
        )
        own_listing = Listing.objects.create(
            product=own_product,
            retailer=retailer,
            external_url='https://ozon.ru/product/own-123'
        )
        rule = AlertRule.objects.create(
            name='Negative Review Alert',
            alert_type='new_negative_review',
            threshold_rating=3,
            channel='telegram',
            recipients=['123'],
            is_active=True
        )
        return {
            'retailer': retailer,
            'product': own_product,
            'listing': own_listing,
            'rule': rule,
        }

    @patch('apps.alerts.tasks.deliver_alert_event.delay')
    def test_negative_review_triggers_alert(self, mock_deliver, setup_review_data):
        """Test that negative review triggers alert."""
        from apps.alerts.tasks import check_review_alerts

        review = ReviewItem.objects.create(
            listing=setup_review_data['listing'],
            external_id='rev-001',
            rating=2,
            text='Плохой товар, не рекомендую'
        )

        result = check_review_alerts(str(review.pk))

        assert result['success'] is True
        assert result['events_created'] == 1
        mock_deliver.assert_called_once()

    @patch('apps.alerts.tasks.deliver_alert_event.delay')
    def test_positive_review_no_alert(self, mock_deliver, setup_review_data):
        """Test that positive review does not trigger alert."""
        from apps.alerts.tasks import check_review_alerts

        review = ReviewItem.objects.create(
            listing=setup_review_data['listing'],
            external_id='rev-002',
            rating=5,
            text='Отличный товар!'
        )

        result = check_review_alerts(str(review.pk))

        assert result['success'] is True
        assert result['events_created'] == 0
        mock_deliver.assert_not_called()


@pytest.mark.django_db
class TestCleanupOldEvents:
    """Tests for old event cleanup."""

    def test_cleanup_deletes_old_delivered_events(self):
        """Test that old delivered events are deleted."""
        from apps.alerts.tasks import cleanup_old_events

        retailer = Retailer.objects.create(
            name='Ozon', slug='ozon', base_url='https://ozon.ru',
            connector_class='apps.scraping.connectors.ozon.OzonConnector'
        )
        product = Product.objects.create(name='Test', brand='Brand', is_own=True)
        listing = Listing.objects.create(
            product=product, retailer=retailer,
            external_url='https://ozon.ru/product/123'
        )
        rule = AlertRule.objects.create(
            name='Test Rule', alert_type='price_increase',
            channel='telegram', recipients=['123']
        )

        # Create an old delivered event
        old_event = AlertEvent.objects.create(
            alert_rule=rule,
            listing=listing,
            message='Old event',
            details={},
            is_delivered=True,
        )
        # Backdate it
        AlertEvent.objects.filter(pk=old_event.pk).update(
            triggered_at=timezone.now() - timedelta(days=100)
        )

        # Create a recent event
        recent_event = AlertEvent.objects.create(
            alert_rule=rule,
            listing=listing,
            message='Recent event',
            details={},
            is_delivered=True,
        )

        result = cleanup_old_events(days=90)

        assert result['deleted'] == 1
        assert AlertEvent.objects.filter(pk=old_event.pk).count() == 0
        assert AlertEvent.objects.filter(pk=recent_event.pk).count() == 1
