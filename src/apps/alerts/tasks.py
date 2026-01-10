"""
Celery tasks for alert processing and notifications.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_price_alerts(snapshot_id: str):
    """
    Check price-related alerts for a new snapshot.

    Args:
        snapshot_id: UUID of the SnapshotPrice
    """
    from apps.scraping.models import SnapshotPrice
    from .models import AlertRule, AlertEvent

    try:
        snapshot = SnapshotPrice.objects.select_related(
            'listing__product', 'listing__retailer'
        ).get(pk=snapshot_id)
    except SnapshotPrice.DoesNotExist:
        logger.error(f'Snapshot {snapshot_id} not found')
        return {'success': False, 'error': 'Snapshot not found'}

    listing = snapshot.listing
    product = listing.product

    # Get previous snapshot for comparison
    previous_snapshot = SnapshotPrice.objects.filter(
        listing=listing,
        scraped_at__lt=snapshot.scraped_at,
    ).order_by('-scraped_at').first()

    if not previous_snapshot:
        return {'success': True, 'message': 'No previous snapshot for comparison'}

    if not snapshot.price_final or not previous_snapshot.price_final:
        return {'success': True, 'message': 'Missing price data'}

    # Calculate price change
    old_price = previous_snapshot.price_final
    new_price = snapshot.price_final
    price_diff = new_price - old_price

    if old_price > 0:
        pct_change = (price_diff / old_price) * 100
    else:
        pct_change = Decimal('0')

    events_created = 0

    # Check price increase alerts
    if price_diff > 0:
        rules = _get_matching_rules(
            AlertRule.AlertTypeChoices.PRICE_INCREASE,
            product,
            listing.retailer,
        )

        for rule in rules:
            if rule.threshold_pct and pct_change >= rule.threshold_pct:
                if _should_trigger(rule, listing):
                    _create_alert_event(
                        rule=rule,
                        listing=listing,
                        snapshot=snapshot,
                        message=f'Цена выросла на {pct_change:.1f}%',
                        details={
                            'old_price': float(old_price),
                            'new_price': float(new_price),
                            'pct_change': float(pct_change),
                        },
                    )
                    events_created += 1

    # Check price decrease alerts
    elif price_diff < 0:
        rules = _get_matching_rules(
            AlertRule.AlertTypeChoices.PRICE_DECREASE,
            product,
            listing.retailer,
        )

        for rule in rules:
            if rule.threshold_pct and abs(pct_change) >= rule.threshold_pct:
                if _should_trigger(rule, listing):
                    _create_alert_event(
                        rule=rule,
                        listing=listing,
                        snapshot=snapshot,
                        message=f'Цена упала на {abs(pct_change):.1f}%',
                        details={
                            'old_price': float(old_price),
                            'new_price': float(new_price),
                            'pct_change': float(pct_change),
                        },
                    )
                    events_created += 1

    # Check out of stock
    if not snapshot.in_stock and previous_snapshot.in_stock:
        rules = _get_matching_rules(
            AlertRule.AlertTypeChoices.OUT_OF_STOCK,
            product,
            listing.retailer,
        )

        for rule in rules:
            if _should_trigger(rule, listing):
                _create_alert_event(
                    rule=rule,
                    listing=listing,
                    snapshot=snapshot,
                    message='Товар закончился',
                    details={'in_stock': False},
                )
                events_created += 1

    return {'success': True, 'events_created': events_created}


@shared_task
def check_review_alerts(review_id: str):
    """
    Check review-related alerts for a new review.

    Args:
        review_id: UUID of the ReviewItem
    """
    from apps.scraping.models import ReviewItem
    from .models import AlertRule, AlertEvent

    try:
        review = ReviewItem.objects.select_related(
            'listing__product', 'listing__retailer'
        ).get(pk=review_id)
    except ReviewItem.DoesNotExist:
        logger.error(f'Review {review_id} not found')
        return {'success': False, 'error': 'Review not found'}

    listing = review.listing
    product = listing.product
    events_created = 0

    # Check negative review alerts for own products
    if product.is_own and review.rating <= 3:
        rules = _get_matching_rules(
            AlertRule.AlertTypeChoices.NEW_NEGATIVE_REVIEW,
            product,
            listing.retailer,
        )

        for rule in rules:
            threshold = rule.threshold_rating or 3
            if review.rating <= threshold:
                if _should_trigger(rule, listing):
                    _create_alert_event(
                        rule=rule,
                        listing=listing,
                        snapshot=None,
                        message=f'Новый негативный отзыв (рейтинг {review.rating})',
                        details={
                            'rating': review.rating,
                            'review_text': review.text[:500] if review.text else '',
                            'review_id': str(review.pk),
                            'author': review.author_name or '',
                        },
                    )
                    events_created += 1

    # Check positive competitor review alerts
    if not product.is_own and review.rating >= 4:
        rules = _get_matching_rules(
            AlertRule.AlertTypeChoices.NEW_POSITIVE_COMPETITOR,
            product,
            listing.retailer,
        )

        for rule in rules:
            threshold = rule.threshold_rating or 4
            if review.rating >= threshold:
                if _should_trigger(rule, listing):
                    _create_alert_event(
                        rule=rule,
                        listing=listing,
                        snapshot=None,
                        message=f'Позитивный отзыв конкурента (рейтинг {review.rating})',
                        details={
                            'rating': review.rating,
                            'review_text': review.text[:500] if review.text else '',
                            'review_id': str(review.pk),
                            'pros': review.pros[:200] if review.pros else '',
                        },
                    )
                    events_created += 1

    return {'success': True, 'events_created': events_created}


@shared_task
def deliver_alert_event(event_id: str):
    """
    Deliver a single alert event via the configured channel.

    Args:
        event_id: UUID of the AlertEvent
    """
    from .models import AlertEvent
    from .telegram_service import TelegramService

    try:
        event = AlertEvent.objects.select_related(
            'alert_rule', 'listing__product', 'listing__retailer'
        ).get(pk=event_id)
    except AlertEvent.DoesNotExist:
        logger.error(f'AlertEvent {event_id} not found')
        return {'success': False, 'error': 'Event not found'}

    if event.is_delivered:
        return {'success': True, 'skipped': True, 'reason': 'Already delivered'}

    rule = event.alert_rule
    listing = event.listing

    if rule.channel == 'telegram':
        service = TelegramService()

        # Send to all recipients
        results = []
        recipients = rule.recipients or []

        # Use default chat if no recipients specified
        if not recipients:
            recipients = [None]  # Will use default chat ID

        for recipient in recipients:
            result = service.send_alert(
                alert_type=rule.alert_type,
                product_name=listing.product.name,
                retailer_name=listing.retailer.name,
                message=event.message,
                details=event.details,
                chat_id=recipient,
            )
            results.append(result)

        # Check if any delivery succeeded
        any_success = any(r.get('success') for r in results)

        if any_success:
            event.is_delivered = True
            event.delivered_at = timezone.now()
            event.save(update_fields=['is_delivered', 'delivered_at', 'updated_at'])
            return {'success': True, 'results': results}
        else:
            errors = [r.get('error', 'Unknown error') for r in results]
            event.delivery_error = '; '.join(errors)
            event.save(update_fields=['delivery_error', 'updated_at'])
            return {'success': False, 'errors': errors}

    elif rule.channel == 'email':
        from .email_service import EmailService

        service = EmailService()

        # Use recipients from rule or default
        recipients = rule.recipients if rule.recipients else None

        result = service.send_alert(
            alert_type=rule.alert_type,
            product_name=listing.product.name,
            retailer_name=listing.retailer.name,
            message=event.message,
            details=event.details,
            recipients=recipients,
        )

        if result.get('success'):
            event.is_delivered = True
            event.delivered_at = timezone.now()
            event.save(update_fields=['is_delivered', 'delivered_at', 'updated_at'])
            return {'success': True, 'result': result}
        else:
            event.delivery_error = result.get('error', 'Unknown error')
            event.save(update_fields=['delivery_error', 'updated_at'])
            return {'success': False, 'error': result.get('error')}

    return {'success': False, 'error': f'Unknown channel: {rule.channel}'}


@shared_task
def deliver_pending_alerts():
    """
    Deliver all pending alert events.
    """
    from .models import AlertEvent

    pending = AlertEvent.objects.filter(
        is_delivered=False,
        delivery_error='',  # Don't retry failed ones automatically
    ).values_list('id', flat=True)[:100]

    queued = 0
    for event_id in pending:
        deliver_alert_event.delay(str(event_id))
        queued += 1

    logger.info(f'Queued {queued} alert events for delivery')
    return {'queued': queued}


@shared_task
def cleanup_old_events(days: int = 90):
    """
    Delete old delivered alert events.

    Args:
        days: Keep events newer than this many days
    """
    from .models import AlertEvent

    cutoff = timezone.now() - timedelta(days=days)

    deleted, _ = AlertEvent.objects.filter(
        is_delivered=True,
        triggered_at__lt=cutoff,
    ).delete()

    logger.info(f'Deleted {deleted} old alert events')
    return {'deleted': deleted}


@shared_task
def send_daily_digest():
    """
    Send a daily email digest of all alerts from the past 24 hours.
    """
    from .models import AlertEvent
    from .email_service import EmailService

    yesterday = timezone.now() - timedelta(hours=24)

    events = AlertEvent.objects.filter(
        triggered_at__gte=yesterday,
    ).select_related(
        'alert_rule', 'listing__product', 'listing__retailer'
    ).order_by('-triggered_at')

    if not events.exists():
        logger.info('No events for daily digest')
        return {'success': True, 'skipped': True, 'reason': 'No events'}

    # Prepare event data for template
    event_data = []
    for event in events:
        event_data.append({
            'alert_type': event.alert_rule.alert_type,
            'alert_type_display': event.alert_rule.get_alert_type_display(),
            'product_name': event.listing.product.name,
            'retailer_name': event.listing.retailer.name,
            'message': event.message,
            'triggered_at': event.triggered_at.strftime('%H:%M'),
        })

    service = EmailService()
    result = service.send_daily_digest(event_data)

    if result.get('success'):
        logger.info(f'Daily digest sent with {len(event_data)} events')
    else:
        logger.error(f'Failed to send daily digest: {result.get("error")}')

    return result


def _get_matching_rules(alert_type: str, product, retailer):
    """Get active rules matching the alert type and scope."""
    from .models import AlertRule

    return AlertRule.objects.filter(
        is_active=True,
        alert_type=alert_type,
    ).filter(
        # Match product OR all products
        Q(product=product) | Q(product__isnull=True)
    ).filter(
        # Match retailer OR all retailers
        Q(retailer=retailer) | Q(retailer__isnull=True)
    )


def _should_trigger(rule, listing) -> bool:
    """Check if the rule should trigger (cooldown check)."""
    from .models import AlertEvent

    if rule.cooldown_hours <= 0:
        return True

    cooldown_since = timezone.now() - timedelta(hours=rule.cooldown_hours)

    recent_event = AlertEvent.objects.filter(
        alert_rule=rule,
        listing=listing,
        triggered_at__gte=cooldown_since,
    ).exists()

    return not recent_event


def _create_alert_event(rule, listing, snapshot, message: str, details: dict):
    """Create and queue an alert event."""
    from .models import AlertEvent

    event = AlertEvent.objects.create(
        alert_rule=rule,
        listing=listing,
        snapshot=snapshot,
        message=message,
        details=details,
    )

    # Queue for immediate delivery
    deliver_alert_event.delay(str(event.pk))

    logger.info(f'Created alert event: {event.pk} for rule {rule.name}')
    return event
