"""
Celery tasks for scraping.
"""
import importlib
import logging
from datetime import date
from celery import shared_task
from asgiref.sync import sync_to_async

from django.utils import timezone

from .browser import BrowserManager, run_sync

logger = logging.getLogger(__name__)


def get_connector_class(connector_path: str):
    """
    Dynamically import and return connector class.

    Args:
        connector_path: Full path like 'apps.scraping.connectors.ozon.OzonConnector'

    Returns:
        Connector class
    """
    module_path, class_name = connector_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


async def scrape_listing_async(listing, session=None):
    """
    Async function to scrape a single listing.

    Args:
        listing: Listing model instance
        session: Optional ScrapeSession

    Returns:
        dict with results
    """
    from apps.scraping.models import SnapshotPrice

    retailer = listing.retailer
    connector_class = get_connector_class(retailer.connector_class)

    # Get session data if available
    session_data = None
    retailer_session = retailer.sessions.filter(is_valid=True).first()
    if retailer_session:
        cookies_json = retailer_session.get_cookies()
        if cookies_json:
            import json
            session_data = {'cookies': json.loads(cookies_json)}

    connector = connector_class(session_data=session_data)

    # Use shared browser manager for efficiency
    async with BrowserManager() as browser:
        result = await connector.scrape_product(listing.external_url, browser)

    if result.success and result.price_data:
        period_month = date.today().replace(day=1)

        snapshot = SnapshotPrice.objects.create(
            listing=listing,
            session=session,
            period_month=period_month,
            price_regular=result.price_data.price_regular,
            price_promo=result.price_data.price_promo,
            price_card=result.price_data.price_card,
            price_final=result.price_data.price_final,
            in_stock=result.price_data.in_stock,
            rating_avg=result.price_data.rating_avg,
            reviews_count=result.price_data.reviews_count,
            raw_data=result.raw_data,
        )

        return {
            'success': True,
            'snapshot_id': str(snapshot.pk),
            'price_final': float(result.price_data.price_final) if result.price_data.price_final else None,
            'rating': result.price_data.rating_avg,
        }
    else:
        return {
            'success': False,
            'error': result.error_message,
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_single_listing(self, listing_id: str, user_id: int = None, session_id: str = None):
    """
    Scrape a single listing.

    Args:
        listing_id: UUID of the Listing
        user_id: Optional user who triggered the scrape
        session_id: Optional existing ScrapeSession ID
    """
    from apps.products.models import Listing
    from apps.scraping.models import ScrapeSession

    try:
        listing = Listing.objects.select_related('retailer', 'product').get(pk=listing_id)
    except Listing.DoesNotExist:
        logger.error(f'Listing {listing_id} not found')
        return {'success': False, 'error': 'Listing not found'}

    logger.info(f'Scraping listing: {listing}')

    # Get or create session
    session = None
    if session_id:
        try:
            session = ScrapeSession.objects.get(pk=session_id)
        except ScrapeSession.DoesNotExist:
            pass

    if not session:
        session = ScrapeSession.objects.create(
            status=ScrapeSession.StatusChoices.RUNNING,
            trigger_type=ScrapeSession.TriggerChoices.MANUAL,
            retailer=listing.retailer,
            listings_total=1,
            started_at=timezone.now(),
            triggered_by_id=user_id,
        )

    try:
        # Run async scraping synchronously
        result = run_sync(scrape_listing_async(listing, session))

        if result['success']:
            listing.last_scraped_at = timezone.now()
            listing.last_scrape_error = ''
            listing.save(update_fields=['last_scraped_at', 'last_scrape_error', 'updated_at'])

            # Update session stats
            if not session_id:  # Only update if we created the session
                session.status = ScrapeSession.StatusChoices.COMPLETED
                session.listings_success = 1
                session.finished_at = timezone.now()
                session.save()

            logger.info(f'Scraping completed for: {listing}, price: {result.get("price_final")}')
            return result

        else:
            raise Exception(result.get('error', 'Unknown error'))

    except Exception as e:
        logger.exception(f'Error scraping {listing}: {e}')

        listing.last_scrape_error = str(e)[:500]
        listing.save(update_fields=['last_scrape_error', 'updated_at'])

        if not session_id:
            session.status = ScrapeSession.StatusChoices.FAILED
            session.listings_failed = 1
            session.error_log = str(e)
            session.finished_at = timezone.now()
            session.save()

        # Retry with exponential backoff
        raise self.retry(exc=e)


@shared_task
def run_scrape_session(session_id: str):
    """
    Run a full scrape session for all active listings.

    Args:
        session_id: UUID of the ScrapeSession
    """
    from apps.products.models import Listing
    from apps.scraping.models import ScrapeSession

    try:
        session = ScrapeSession.objects.get(pk=session_id)
    except ScrapeSession.DoesNotExist:
        logger.error(f'Session {session_id} not found')
        return

    logger.info(f'Starting scrape session: {session}')

    session.status = ScrapeSession.StatusChoices.RUNNING
    session.started_at = timezone.now()
    session.save()

    # Get all active listings
    listings = Listing.objects.filter(
        is_active=True,
        retailer__is_active=True,
    ).select_related('retailer', 'product')

    if session.retailer:
        listings = listings.filter(retailer=session.retailer)

    listings = listings.order_by('-scrape_priority')

    session.listings_total = listings.count()
    session.save(update_fields=['listings_total'])

    queued_count = 0
    errors = []

    for listing in listings:
        try:
            # Queue individual scrape task with session reference
            scrape_single_listing.delay(
                str(listing.pk),
                user_id=session.triggered_by_id,
                session_id=str(session.pk),
            )
            queued_count += 1
        except Exception as e:
            errors.append(f'{listing}: {e}')
            logger.exception(f'Error queueing scrape for {listing}')

    if errors:
        session.error_log = '\n'.join(errors)
        session.save(update_fields=['error_log'])

    logger.info(f'Scrape session {session_id}: queued {queued_count} tasks')

    return {
        'session_id': session_id,
        'queued': queued_count,
        'errors': len(errors),
    }


@shared_task
def update_session_stats(session_id: str):
    """
    Update session statistics after all tasks complete.
    Called periodically or after batch completion.
    """
    from apps.scraping.models import ScrapeSession, SnapshotPrice

    try:
        session = ScrapeSession.objects.get(pk=session_id)
    except ScrapeSession.DoesNotExist:
        return

    # Count successful snapshots
    success_count = SnapshotPrice.objects.filter(session=session).count()

    session.listings_success = success_count
    session.listings_failed = session.listings_total - success_count

    if session.listings_success + session.listings_failed >= session.listings_total:
        session.status = ScrapeSession.StatusChoices.COMPLETED
        session.finished_at = timezone.now()

    session.save()


@shared_task
def scheduled_monthly_scrape():
    """
    Scheduled task for monthly scraping.
    Triggered by Celery Beat on the 1st of each month.
    """
    from apps.scraping.models import ScrapeSession

    logger.info('Starting scheduled monthly scrape')

    session = ScrapeSession.objects.create(
        trigger_type=ScrapeSession.TriggerChoices.SCHEDULED,
    )

    run_scrape_session.delay(str(session.pk))
    return {'session_id': str(session.pk)}


# ============= Review Scraping Tasks =============

async def scrape_reviews_async(listing, session=None, max_reviews=50):
    """
    Async function to scrape reviews for a listing.

    Args:
        listing: Listing model instance
        session: Optional ScrapeSession
        max_reviews: Maximum reviews to collect

    Returns:
        dict with results
    """
    from apps.scraping.models import ReviewItem, SnapshotReview
    import json

    retailer = listing.retailer
    connector_class = get_connector_class(retailer.connector_class)

    # Get session data if available
    session_data = None
    retailer_session = retailer.sessions.filter(is_valid=True).first()
    if retailer_session:
        cookies_json = retailer_session.get_cookies()
        if cookies_json:
            session_data = {'cookies': json.loads(cookies_json)}

    connector = connector_class(session_data=session_data)

    # Scrape reviews
    async with BrowserManager() as browser:
        reviews_data = await connector.scrape_reviews(
            listing.external_url,
            browser,
            max_reviews=max_reviews,
        )

    if not reviews_data:
        return {
            'success': True,
            'reviews_collected': 0,
            'reviews_new': 0,
        }

    # Save reviews to database
    reviews_new = 0
    reviews_by_rating = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for review_data in reviews_data:
        # Check if review already exists
        existing = ReviewItem.objects.filter(
            listing=listing,
            external_id=review_data.external_id,
        ).first()

        if existing:
            # Update if needed
            continue

        # Create new review
        ReviewItem.objects.create(
            listing=listing,
            external_id=review_data.external_id,
            rating=review_data.rating,
            text=review_data.text,
            author_name=review_data.author_name,
            pros=review_data.pros,
            cons=review_data.cons,
            published_at=review_data.published_at,
            raw_data=review_data.raw_data,
        )
        reviews_new += 1
        if 1 <= review_data.rating <= 5:
            reviews_by_rating[review_data.rating] += 1

    # Create review snapshot
    period_month = date.today().replace(day=1)

    # Get total counts from all reviews for this listing
    from django.db.models import Count
    rating_counts = ReviewItem.objects.filter(
        listing=listing
    ).values('rating').annotate(count=Count('rating'))

    rating_totals = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for item in rating_counts:
        rating_totals[item['rating']] = item['count']

    SnapshotReview.objects.create(
        listing=listing,
        session=session,
        period_month=period_month,
        reviews_1_count=rating_totals[1],
        reviews_2_count=rating_totals[2],
        reviews_3_count=rating_totals[3],
        reviews_4_count=rating_totals[4],
        reviews_5_count=rating_totals[5],
        new_reviews_count=reviews_new,
    )

    return {
        'success': True,
        'reviews_collected': len(reviews_data),
        'reviews_new': reviews_new,
        'by_rating': reviews_by_rating,
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def scrape_listing_reviews(self, listing_id: str, session_id: str = None, max_reviews: int = 50):
    """
    Scrape reviews for a single listing.

    Args:
        listing_id: UUID of the Listing
        session_id: Optional existing ScrapeSession ID
        max_reviews: Maximum reviews to collect
    """
    from apps.products.models import Listing
    from apps.scraping.models import ScrapeSession

    try:
        listing = Listing.objects.select_related('retailer', 'product').get(pk=listing_id)
    except Listing.DoesNotExist:
        logger.error(f'Listing {listing_id} not found')
        return {'success': False, 'error': 'Listing not found'}

    logger.info(f'Scraping reviews for: {listing}')

    session = None
    if session_id:
        try:
            session = ScrapeSession.objects.get(pk=session_id)
        except ScrapeSession.DoesNotExist:
            pass

    try:
        result = run_sync(scrape_reviews_async(listing, session, max_reviews))
        logger.info(f'Reviews scraped for {listing}: {result}')
        return result

    except Exception as e:
        logger.exception(f'Error scraping reviews for {listing}: {e}')
        raise self.retry(exc=e)


@shared_task
def scrape_all_reviews(max_reviews_per_listing: int = 50):
    """
    Scrape reviews for all active listings.
    Typically run monthly.
    """
    from apps.products.models import Listing
    from apps.scraping.models import ScrapeSession

    logger.info('Starting reviews scrape for all listings')

    session = ScrapeSession.objects.create(
        trigger_type=ScrapeSession.TriggerChoices.SCHEDULED,
    )

    listings = Listing.objects.filter(
        is_active=True,
        retailer__is_active=True,
    ).select_related('retailer')

    session.listings_total = listings.count()
    session.status = ScrapeSession.StatusChoices.RUNNING
    session.started_at = timezone.now()
    session.save()

    queued = 0
    for listing in listings:
        try:
            scrape_listing_reviews.delay(
                str(listing.pk),
                session_id=str(session.pk),
                max_reviews=max_reviews_per_listing,
            )
            queued += 1
        except Exception as e:
            logger.exception(f'Error queueing review scrape for {listing}: {e}')

    logger.info(f'Queued {queued} review scraping tasks')
    return {'session_id': str(session.pk), 'queued': queued}


# ============= Maintenance Tasks =============

@shared_task
def cleanup_stale_sessions():
    """
    Cleanup stale scrape sessions that got stuck.
    Marks sessions running for more than 2 hours as failed.
    """
    from datetime import timedelta
    from apps.scraping.models import ScrapeSession

    stale_threshold = timezone.now() - timedelta(hours=2)

    stale_sessions = ScrapeSession.objects.filter(
        status=ScrapeSession.StatusChoices.RUNNING,
        started_at__lt=stale_threshold,
    )

    count = 0
    for session in stale_sessions:
        session.status = ScrapeSession.StatusChoices.FAILED
        session.error_log = 'Session timed out (running > 2 hours)'
        session.finished_at = timezone.now()
        session.save()
        count += 1
        logger.warning(f'Marked stale session as failed: {session.pk}')

    # Also update session statistics
    pending_sessions = ScrapeSession.objects.filter(
        status=ScrapeSession.StatusChoices.RUNNING,
    )

    for session in pending_sessions:
        try:
            update_session_stats(str(session.pk))
        except Exception as e:
            logger.exception(f'Error updating session stats for {session.pk}: {e}')

    return {'stale_sessions_cleaned': count}


@shared_task
def cleanup_old_snapshots(days: int = 365):
    """
    Delete old price snapshots beyond retention period.
    Keeps at least one snapshot per month for historical data.

    Args:
        days: Delete snapshots older than this many days (default 1 year)
    """
    from datetime import timedelta
    from django.db.models import Min
    from apps.scraping.models import SnapshotPrice

    cutoff_date = timezone.now() - timedelta(days=days)
    cutoff_month = cutoff_date.replace(day=1).date()

    logger.info(f'Cleaning up snapshots older than {cutoff_date}')

    # Get the minimum scraped_at for each listing/month combo to keep
    # We want to keep at least one snapshot per listing per month for trends
    snapshots_to_keep = set()

    # For each month before cutoff, keep one snapshot per listing
    keep_snapshots = SnapshotPrice.objects.filter(
        scraped_at__lt=cutoff_date,
    ).values('listing_id', 'period_month').annotate(
        first_id=Min('id')
    )

    for item in keep_snapshots:
        snapshots_to_keep.add(item['first_id'])

    # Delete old snapshots except the ones we want to keep
    deleted_count, _ = SnapshotPrice.objects.filter(
        scraped_at__lt=cutoff_date,
    ).exclude(
        id__in=snapshots_to_keep
    ).delete()

    logger.info(f'Deleted {deleted_count} old snapshots, kept {len(snapshots_to_keep)} for historical trends')

    return {
        'deleted': deleted_count,
        'kept_for_history': len(snapshots_to_keep),
    }


@shared_task
def cleanup_old_reviews(days: int = 730):
    """
    Archive or delete very old reviews.
    By default keeps 2 years of reviews.

    Args:
        days: Delete reviews older than this many days
    """
    from datetime import timedelta
    from apps.scraping.models import ReviewItem

    cutoff_date = timezone.now() - timedelta(days=days)

    deleted_count, _ = ReviewItem.objects.filter(
        published_at__lt=cutoff_date,
    ).delete()

    logger.info(f'Deleted {deleted_count} reviews older than {cutoff_date}')

    return {'deleted': deleted_count}


@shared_task
def cleanup_old_sessions(days: int = 90):
    """
    Delete old completed scrape sessions.

    Args:
        days: Delete sessions older than this many days
    """
    from datetime import timedelta
    from apps.scraping.models import ScrapeSession

    cutoff_date = timezone.now() - timedelta(days=days)

    deleted_count, _ = ScrapeSession.objects.filter(
        status__in=[
            ScrapeSession.StatusChoices.COMPLETED,
            ScrapeSession.StatusChoices.FAILED,
        ],
        finished_at__lt=cutoff_date,
    ).delete()

    logger.info(f'Deleted {deleted_count} old scrape sessions')

    return {'deleted': deleted_count}


@shared_task
def cleanup_raw_data(days: int = 30):
    """
    Clear raw_data JSON from old snapshots to save space.
    Keeps raw data for recent snapshots only.

    Args:
        days: Clear raw_data from snapshots older than this
    """
    from datetime import timedelta
    from apps.scraping.models import SnapshotPrice

    cutoff_date = timezone.now() - timedelta(days=days)

    # Clear raw_data field for old snapshots
    updated = SnapshotPrice.objects.filter(
        scraped_at__lt=cutoff_date,
        raw_data__isnull=False,
    ).exclude(
        raw_data={}
    ).update(raw_data={})

    logger.info(f'Cleared raw_data from {updated} old snapshots')

    return {'cleared': updated}


@shared_task
def vacuum_database():
    """
    Run VACUUM ANALYZE on PostgreSQL to reclaim space and update statistics.
    Should be run periodically (weekly) after cleanup tasks.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            # VACUUM cannot run inside a transaction block
            cursor.execute('VACUUM ANALYZE')
        logger.info('Database VACUUM ANALYZE completed')
        return {'success': True}
    except Exception as e:
        logger.error(f'VACUUM failed: {e}')
        return {'success': False, 'error': str(e)}


@shared_task
def run_all_cleanups():
    """
    Run all cleanup tasks in sequence.
    Designed to be run weekly via Celery Beat.
    """
    results = {}

    # Run cleanups
    results['snapshots'] = cleanup_old_snapshots()
    results['reviews'] = cleanup_old_reviews()
    results['sessions'] = cleanup_old_sessions()
    results['raw_data'] = cleanup_raw_data()
    results['stale_sessions'] = cleanup_stale_sessions()

    # Alert events cleanup
    from apps.alerts.tasks import cleanup_old_events
    results['alert_events'] = cleanup_old_events()

    logger.info(f'All cleanups completed: {results}')

    return results


# ============= Manual Import Tasks =============

async def _scrape_product_async(connector, url, scrape_reviews: bool = True):
    """
    Async helper to run browser scraping only.
    Returns tuple of (result, reviews_list).
    """
    async with BrowserManager() as browser:
        result = await connector.scrape_product(url, browser)

        reviews_list = []
        if result.success and result.price_data and scrape_reviews:
            try:
                reviews_data = await connector.scrape_reviews(
                    url,
                    browser,
                    max_reviews=30,
                )
                for review in reviews_data:
                    reviews_list.append({
                        'rating': review.rating,
                        'text': review.text[:500] if review.text else '',
                        'author': review.author_name,
                        'pros': review.pros[:300] if review.pros else '',
                        'cons': review.cons[:300] if review.cons else '',
                        'date': review.published_at.isoformat() if review.published_at else None,
                    })
            except Exception as e:
                logger.warning(f'Error scraping reviews: {e}')

        return result, reviews_list


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_manual_import(self, import_id: str, scrape_reviews: bool = True):
    """
    Process a manual URL import (synchronous task with async browser scraping).

    Args:
        import_id: UUID of the ManualImport
        scrape_reviews: Whether to also scrape reviews
    """
    from apps.scraping.models import ManualImport
    from apps.scraping.connectors import get_connector

    logger.info(f'Processing manual import: {import_id}')

    try:
        # Get import object (sync ORM call)
        try:
            import_obj = ManualImport.objects.get(pk=import_id)
        except ManualImport.DoesNotExist:
            return {'success': False, 'error': 'Import not found'}

        # Update status
        import_obj.status = ManualImport.StatusChoices.PROCESSING
        import_obj.save(update_fields=['status', 'updated_at'])

        # Detect retailer
        retailer = import_obj.detect_retailer()
        if not retailer:
            import_obj.status = ManualImport.StatusChoices.FAILED
            import_obj.error_message = 'Не удалось определить магазин из URL'
            import_obj.processed_at = timezone.now()
            import_obj.save()
            return {'success': False, 'error': 'Unknown retailer'}

        import_obj.retailer = retailer
        import_obj.save(update_fields=['retailer'])

        # Get connector class
        connector_cls = get_connector(retailer.slug)
        if not connector_cls:
            import_obj.status = ManualImport.StatusChoices.FAILED
            import_obj.error_message = f'Коннектор для {retailer.name} не найден'
            import_obj.processed_at = timezone.now()
            import_obj.save()
            return {'success': False, 'error': 'Connector not found'}

        connector = connector_cls()

        # Run async browser scraping in separate thread
        result, reviews_list = run_sync(_scrape_product_async(connector, import_obj.url, scrape_reviews))

        # Process results (sync ORM calls)
        if result.success and result.price_data:
            import_obj.product_title = result.price_data.title or ''
            import_obj.price_regular = result.price_data.price_regular
            import_obj.price_promo = result.price_data.price_promo
            import_obj.price_final = result.price_data.price_final
            import_obj.rating = result.price_data.rating_avg
            import_obj.reviews_count = result.price_data.reviews_count
            import_obj.in_stock = result.price_data.in_stock
            import_obj.raw_data = result.raw_data or {}
            import_obj.reviews_data = reviews_list

            # Analyze reviews for insights
            if reviews_list:
                import_obj.analyze_reviews()

            # Calculate price change from previous period
            import_obj.calculate_price_change()

            import_obj.status = ManualImport.StatusChoices.COMPLETED
            import_obj.processed_at = timezone.now()
            import_obj.save()

            logger.info(f'Manual import {import_id} completed: {import_obj.product_title}')
            return {
                'success': True,
                'title': import_obj.product_title,
                'price': float(import_obj.price_final) if import_obj.price_final else None,
                'reviews_count': len(reviews_list),
                'insights': import_obj.review_insights,
            }
        else:
            import_obj.status = ManualImport.StatusChoices.FAILED
            import_obj.error_message = result.error_message or 'Не удалось получить данные'
            import_obj.raw_data = result.raw_data or {}
            import_obj.processed_at = timezone.now()
            import_obj.save()

            return {'success': False, 'error': result.error_message}

    except Exception as e:
        logger.exception(f'Error processing manual import {import_id}: {e}')

        # Update status on failure
        try:
            import_obj = ManualImport.objects.get(pk=import_id)
            import_obj.status = ManualImport.StatusChoices.FAILED
            import_obj.error_message = str(e)[:500]
            import_obj.processed_at = timezone.now()
            import_obj.save()
        except ManualImport.DoesNotExist:
            pass

        raise self.retry(exc=e)


# ============= Scheduled Monthly Monitoring =============

@shared_task
def run_monthly_monitoring():
    """
    Scheduled task for monthly product monitoring.
    Collects data for all products marked as recurring.
    Triggered by Celery Beat on the 1st or 10th of each month.
    """
    from apps.scraping.models import ManualImport

    logger.info('Starting scheduled monthly monitoring')

    # Get all recurring imports
    recurring_imports = ManualImport.objects.filter(
        is_recurring=True,
        status=ManualImport.StatusChoices.COMPLETED,
    ).values('user_id', 'url', 'product_type', 'group_id', 'custom_name')

    # Group by unique URL per user to avoid duplicates
    seen = set()
    imports_to_create = []

    for imp in recurring_imports:
        key = (imp['user_id'], imp['url'])
        if key not in seen:
            seen.add(key)
            imports_to_create.append(imp)

    # Create new imports for this month
    created_count = 0
    current_period = date.today().replace(day=1)

    for imp_data in imports_to_create:
        # Check if already have data for this month
        existing = ManualImport.objects.filter(
            user_id=imp_data['user_id'],
            url=imp_data['url'],
            monitoring_period=current_period,
        ).exists()

        if existing:
            continue

        # Create new import
        new_import = ManualImport.objects.create(
            user_id=imp_data['user_id'],
            url=imp_data['url'],
            product_type=imp_data['product_type'],
            group_id=imp_data['group_id'],
            custom_name=imp_data['custom_name'] or '',
            monitoring_period=current_period,
            is_recurring=True,
        )

        # Queue processing
        process_manual_import.delay(str(new_import.pk), scrape_reviews=True)
        created_count += 1

    logger.info(f'Monthly monitoring: created {created_count} new imports')

    return {
        'created': created_count,
        'period': current_period.isoformat(),
    }


@shared_task
def send_monthly_monitoring_report():
    """
    Send a summary report after monthly monitoring completes.
    Should be scheduled a few hours after run_monthly_monitoring.
    """
    from django.contrib.auth import get_user_model
    from apps.scraping.models import ManualImport

    User = get_user_model()
    current_period = date.today().replace(day=1)

    logger.info('Generating monthly monitoring reports')

    reports_sent = 0

    # Get all users with monitoring data
    users_with_data = ManualImport.objects.filter(
        monitoring_period=current_period,
        status=ManualImport.StatusChoices.COMPLETED,
    ).values_list('user_id', flat=True).distinct()

    for user_id in users_with_data:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            continue

        # Get user's imports for this period
        imports = ManualImport.objects.filter(
            user=user,
            monitoring_period=current_period,
            status=ManualImport.StatusChoices.COMPLETED,
        )

        own_imports = imports.filter(product_type='own')
        competitor_imports = imports.filter(product_type='competitor')

        # Calculate stats
        price_increases = imports.filter(price_change__gt=0).count()
        negative_reviews = own_imports.filter(reviews_negative_count__gt=0).count()

        # Log summary (could be extended to send email/Telegram)
        logger.info(
            f'Monthly report for {user.email}: '
            f'{own_imports.count()} own products, '
            f'{competitor_imports.count()} competitors, '
            f'{price_increases} price increases, '
            f'{negative_reviews} with negative reviews'
        )
        reports_sent += 1

    return {'reports_sent': reports_sent}
