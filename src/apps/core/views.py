from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Avg, Count, Q, Sum, Max, Subquery, OuterRef
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView

from datetime import timedelta


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view with key metrics."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'

        # Import models here to avoid circular imports
        from apps.products.models import Product, Listing
        from apps.retailers.models import Retailer
        from apps.scraping.models import ScrapeSession, SnapshotPrice, ReviewItem
        from apps.alerts.models import AlertRule, AlertEvent

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # Basic counts
        context['products_count'] = Product.objects.count()
        context['products_own_count'] = Product.objects.filter(is_own=True).count()
        context['products_competitor_count'] = Product.objects.filter(is_own=False).count()
        context['listings_count'] = Listing.objects.filter(is_active=True).count()
        context['retailers_count'] = Retailer.objects.filter(is_active=True).count()

        # Scraping stats
        last_session = ScrapeSession.objects.filter(
            status='completed'
        ).order_by('-finished_at').first()
        context['last_session'] = last_session

        context['sessions_30d'] = ScrapeSession.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()

        context['sessions_success_30d'] = ScrapeSession.objects.filter(
            created_at__gte=thirty_days_ago,
            status='completed'
        ).count()

        # Price snapshots
        context['snapshots_count'] = SnapshotPrice.objects.count()
        context['snapshots_30d'] = SnapshotPrice.objects.filter(
            scraped_at__gte=thirty_days_ago
        ).count()

        # Reviews stats
        context['reviews_total'] = ReviewItem.objects.count()
        context['reviews_30d'] = ReviewItem.objects.filter(
            scraped_at__gte=thirty_days_ago
        ).count()
        context['reviews_negative'] = ReviewItem.objects.filter(
            rating__lte=3
        ).count()
        context['reviews_unprocessed'] = ReviewItem.objects.filter(
            is_processed=False
        ).count()

        # Alerts stats
        context['alerts_active'] = AlertRule.objects.filter(is_active=True).count()
        context['alerts_total'] = AlertRule.objects.count()
        context['alert_events_7d'] = AlertEvent.objects.filter(
            triggered_at__gte=seven_days_ago
        ).count()
        context['alert_events_pending'] = AlertEvent.objects.filter(
            is_delivered=False
        ).count()

        # Recent alert events
        context['recent_alerts'] = AlertEvent.objects.select_related(
            'alert_rule', 'listing__product', 'listing__retailer'
        ).order_by('-triggered_at')[:5]

        # Retailers with listing counts
        context['retailers'] = Retailer.objects.filter(
            is_active=True
        ).annotate(
            listings_count=Count('listings', filter=Q(listings__is_active=True))
        ).order_by('name')

        # Average rating by retailer (from latest snapshots)
        retailer_ratings = []
        for retailer in context['retailers']:
            # Get latest snapshot per listing using subquery
            latest_snapshot_subquery = SnapshotPrice.objects.filter(
                listing_id=OuterRef('listing_id'),
                rating_avg__isnull=False
            ).order_by('-scraped_at').values('scraped_at')[:1]

            # Get average rating from latest snapshots
            avg_rating = SnapshotPrice.objects.filter(
                listing__retailer=retailer,
                rating_avg__isnull=False,
                scraped_at=Subquery(latest_snapshot_subquery)
            ).aggregate(avg=Avg('rating_avg'))['avg']

            retailer_ratings.append({
                'retailer': retailer,
                'avg_rating': round(avg_rating, 2) if avg_rating else None,
                'listings_count': retailer.listings_count
            })
        context['retailer_ratings'] = retailer_ratings

        # Products with issues (low ratings or many negative reviews)
        products_with_issues = []
        for product in Product.objects.filter(is_own=True)[:20]:
            negative_reviews = ReviewItem.objects.filter(
                listing__product=product,
                rating__lte=3
            ).count()
            latest_snapshot = SnapshotPrice.objects.filter(
                listing__product=product,
                rating_avg__isnull=False
            ).order_by('-scraped_at').first()

            if negative_reviews >= 3 or (latest_snapshot and latest_snapshot.rating_avg and latest_snapshot.rating_avg < 4):
                products_with_issues.append({
                    'product': product,
                    'negative_reviews': negative_reviews,
                    'avg_rating': latest_snapshot.rating_avg if latest_snapshot else None
                })

        context['products_with_issues'] = sorted(
            products_with_issues,
            key=lambda x: (x['negative_reviews'], -(x['avg_rating'] or 5)),
            reverse=True
        )[:5]

        # Recent scraping sessions
        context['recent_sessions'] = ScrapeSession.objects.select_related(
            'retailer', 'triggered_by'
        ).order_by('-created_at')[:5]

        return context


def health_check(request):
    """Health check endpoint for monitoring."""
    from django.db import connection

    health_data = {
        'status': 'ok',
        'service': 'retail_monitor',
        'checks': {},
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_data['checks']['database'] = 'ok'
    except Exception as e:
        health_data['status'] = 'degraded'
        health_data['checks']['database'] = str(e)

    # Check Redis/Celery broker
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_data['checks']['cache'] = 'ok'
        else:
            health_data['checks']['cache'] = 'read failed'
    except Exception as e:
        health_data['status'] = 'degraded'
        health_data['checks']['cache'] = str(e)

    status_code = 200 if health_data['status'] == 'ok' else 503
    return JsonResponse(health_data, status=status_code)


def ready_check(request):
    """Readiness check for Kubernetes/Docker."""
    from django.db import connection
    from django.core.cache import cache

    try:
        # Database check
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')

        # Cache check
        cache.set('ready_check', 'ok', 10)
        cache.get('ready_check')

        return JsonResponse({'status': 'ready'})
    except Exception as e:
        return JsonResponse({'status': 'not_ready', 'error': str(e)}, status=503)


# ============= API Endpoints for Charts =============

def api_price_trends(request):
    """API endpoint for price trend chart data."""
    from apps.scraping.models import SnapshotPrice
    from django.db.models.functions import TruncMonth
    from django.contrib.auth.decorators import login_required

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Get last 6 months of price data
    six_months_ago = timezone.now() - timedelta(days=180)

    price_data = SnapshotPrice.objects.filter(
        scraped_at__gte=six_months_ago,
        price_final__isnull=False
    ).annotate(
        month=TruncMonth('scraped_at')
    ).values('month').annotate(
        avg_price=Avg('price_final'),
        min_price=models.Min('price_final'),
        max_price=models.Max('price_final'),
        count=Count('id')
    ).order_by('month')

    labels = []
    avg_prices = []
    min_prices = []
    max_prices = []

    for item in price_data:
        labels.append(item['month'].strftime('%b %Y'))
        avg_prices.append(float(item['avg_price']) if item['avg_price'] else 0)
        min_prices.append(float(item['min_price']) if item['min_price'] else 0)
        max_prices.append(float(item['max_price']) if item['max_price'] else 0)

    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Средняя цена',
                'data': avg_prices,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'fill': True,
            },
            {
                'label': 'Мин. цена',
                'data': min_prices,
                'borderColor': 'rgb(54, 162, 235)',
                'borderDash': [5, 5],
            },
            {
                'label': 'Макс. цена',
                'data': max_prices,
                'borderColor': 'rgb(255, 99, 132)',
                'borderDash': [5, 5],
            },
        ]
    })


def api_reviews_by_rating(request):
    """API endpoint for reviews distribution by rating."""
    from apps.scraping.models import ReviewItem

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    rating_counts = ReviewItem.objects.values('rating').annotate(
        count=Count('id')
    ).order_by('rating')

    labels = ['1 звезда', '2 звезды', '3 звезды', '4 звезды', '5 звёзд']
    data = [0, 0, 0, 0, 0]
    colors = [
        'rgb(255, 99, 132)',   # Red for 1
        'rgb(255, 159, 64)',   # Orange for 2
        'rgb(255, 205, 86)',   # Yellow for 3
        'rgb(75, 192, 192)',   # Teal for 4
        'rgb(54, 162, 235)',   # Blue for 5
    ]

    for item in rating_counts:
        if 1 <= item['rating'] <= 5:
            data[item['rating'] - 1] = item['count']

    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors,
        }]
    })


def api_reviews_trend(request):
    """API endpoint for reviews trend over time."""
    from apps.scraping.models import ReviewItem
    from django.db.models.functions import TruncMonth

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    six_months_ago = timezone.now() - timedelta(days=180)

    reviews_data = ReviewItem.objects.filter(
        scraped_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('scraped_at')
    ).values('month').annotate(
        total=Count('id'),
        positive=Count('id', filter=Q(rating__gte=4)),
        negative=Count('id', filter=Q(rating__lte=3)),
    ).order_by('month')

    labels = []
    positive = []
    negative = []

    for item in reviews_data:
        labels.append(item['month'].strftime('%b %Y'))
        positive.append(item['positive'])
        negative.append(item['negative'])

    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Позитивные (4-5)',
                'data': positive,
                'backgroundColor': 'rgba(75, 192, 192, 0.8)',
            },
            {
                'label': 'Негативные (1-3)',
                'data': negative,
                'backgroundColor': 'rgba(255, 99, 132, 0.8)',
            },
        ]
    })


def api_retailer_comparison(request):
    """API endpoint for retailer comparison data."""
    from apps.retailers.models import Retailer
    from apps.scraping.models import SnapshotPrice
    from apps.products.models import Listing

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    retailers = Retailer.objects.filter(is_active=True)

    labels = []
    listings_data = []
    avg_prices = []
    avg_ratings = []

    for retailer in retailers:
        labels.append(retailer.name)

        # Count active listings
        listings_count = Listing.objects.filter(
            retailer=retailer,
            is_active=True
        ).count()
        listings_data.append(listings_count)

        # Get average price from recent snapshots
        avg_price = SnapshotPrice.objects.filter(
            listing__retailer=retailer,
            price_final__isnull=False,
            scraped_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(avg=Avg('price_final'))['avg']
        avg_prices.append(float(avg_price) if avg_price else 0)

        # Get average rating
        avg_rating = SnapshotPrice.objects.filter(
            listing__retailer=retailer,
            rating_avg__isnull=False,
            scraped_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(avg=Avg('rating_avg'))['avg']
        avg_ratings.append(float(avg_rating) if avg_rating else 0)

    return JsonResponse({
        'labels': labels,
        'listings': listings_data,
        'avg_prices': avg_prices,
        'avg_ratings': avg_ratings,
    })


def api_scraping_activity(request):
    """API endpoint for scraping activity over time."""
    from apps.scraping.models import ScrapeSession
    from django.db.models.functions import TruncDate

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    thirty_days_ago = timezone.now() - timedelta(days=30)

    sessions = ScrapeSession.objects.filter(
        created_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
    ).order_by('date')

    labels = []
    success_data = []
    failed_data = []

    for item in sessions:
        labels.append(item['date'].strftime('%d.%m'))
        success_data.append(item['success'])
        failed_data.append(item['failed'])

    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Успешные',
                'data': success_data,
                'backgroundColor': 'rgba(75, 192, 192, 0.8)',
            },
            {
                'label': 'Ошибки',
                'data': failed_data,
                'backgroundColor': 'rgba(255, 99, 132, 0.8)',
            },
        ]
    })
