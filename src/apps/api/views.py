"""
REST API views for Retail Monitor.
Provides JSON endpoints for external integrations.
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def json_response(data, status=200):
    """Helper to return JSON response with proper encoder."""
    return JsonResponse(data, status=status, encoder=DecimalEncoder, safe=False)


def api_error(message, status=400):
    """Return error JSON response."""
    return JsonResponse({'error': message, 'success': False}, status=status)


# ============= Health Check =============

@require_GET
def health_check(request):
    """
    Health check endpoint for Railway deployment.
    Returns 200 if the service is healthy.
    """
    from django.db import connection

    health = {
        'status': 'healthy',
        'database': 'ok',
        'timestamp': timezone.now().isoformat(),
    }

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['database'] = 'ok'
    except Exception as e:
        health['status'] = 'unhealthy'
        health['database'] = str(e)
        return JsonResponse(health, status=503)

    return JsonResponse(health)


# ============= Authentication API =============

@ensure_csrf_cookie
@require_GET
def get_csrf_token(request):
    """
    Get CSRF token for the frontend.
    The token is set in the cookie by ensure_csrf_cookie decorator.
    """
    return JsonResponse({
        'success': True,
        'csrfToken': get_token(request),
    })


@csrf_exempt
@require_POST
def api_login(request):
    """
    Login endpoint for the frontend.
    Returns JSON response instead of redirect.
    """
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return api_error('Invalid JSON body')

    username = body.get('username')
    password = body.get('password')

    if not username or not password:
        return api_error('Username and password are required')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        })
    else:
        return api_error('Invalid credentials', 401)


@require_POST
def api_logout(request):
    """Logout endpoint for the frontend."""
    logout(request)
    return JsonResponse({'success': True})


@require_GET
def check_auth(request):
    """Check if user is authenticated."""
    if request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }
        })
    return JsonResponse({
        'success': True,
        'authenticated': False,
    })


# ============= Products API =============

@require_GET
def products_list(request):
    """
    List all products with optional filtering.

    Query params:
        - is_own: Filter by own products (true/false)
        - brand: Filter by brand name
        - search: Search in name
        - limit: Max results (default 50)
        - offset: Pagination offset
    """
    try:
        from apps.products.models import Product

        products = Product.objects.all()

        # Apply filters
        if request.GET.get('is_own'):
            is_own = request.GET.get('is_own').lower() == 'true'
            products = products.filter(is_own=is_own)

        if request.GET.get('brand'):
            products = products.filter(brand__icontains=request.GET.get('brand'))

        if request.GET.get('search'):
            products = products.filter(name__icontains=request.GET.get('search'))

        # Pagination
        limit = min(int(request.GET.get('limit', 50)), 100)
        offset = int(request.GET.get('offset', 0))

        total = products.count()
        products = products.order_by('-created_at')[offset:offset + limit]

        data = {
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'products': [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'brand': p.brand or '',
                    'sku': '',  # Product model doesn't have sku
                    'is_own': p.is_own,
                    'category': None,  # Product model doesn't have category
                    'created_at': p.created_at.isoformat() if p.created_at else None,
                }
                for p in products
            ]
        }

        return json_response(data)
    except Exception as e:
        return api_error(f'Error fetching products: {str(e)}', 500)


@require_GET
def product_detail(request, product_id):
    """
    Get detailed product info including listings and latest prices.
    """
    try:
        from apps.products.models import Product, Listing
        from apps.scraping.models import SnapshotPrice

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return api_error('Product not found', 404)

        listings = Listing.objects.filter(product=product, is_active=True)

        listings_data = []
        for listing in listings:
            # Get latest snapshot
            latest_snapshot = SnapshotPrice.objects.filter(
                listing=listing
            ).order_by('-scraped_at').first()

            listings_data.append({
                'id': str(listing.id),
                'retailer': listing.retailer.name,
                'external_url': listing.external_url,
                'last_scraped': listing.last_scraped_at.isoformat() if listing.last_scraped_at else None,
                'latest_price': {
                    'price_final': latest_snapshot.price_final,
                    'price_regular': latest_snapshot.price_regular,
                    'in_stock': latest_snapshot.in_stock,
                    'rating_avg': latest_snapshot.rating_avg,
                    'reviews_count': latest_snapshot.reviews_count,
                    'scraped_at': latest_snapshot.scraped_at.isoformat(),
                } if latest_snapshot else None,
            })

        data = {
            'success': True,
            'product': {
                'id': str(product.id),
                'name': product.name,
                'brand': product.brand,
                'sku': '',  # Not in model
                'barcode': '',  # Not in model
                'is_own': product.is_own,
                'category': None,  # Not in model
                'description': product.notes,  # Use notes as description
                'created_at': product.created_at.isoformat(),
            },
            'listings': listings_data,
        }

        return json_response(data)
    except Exception as e:
        return api_error(f'Error fetching product: {str(e)}', 500)


# ============= Retailers API =============

@require_GET
def retailers_list(request):
    """List all active retailers."""
    try:
        from apps.retailers.models import Retailer

        retailers = Retailer.objects.filter(is_active=True)

        data = {
            'success': True,
            'retailers': [
                {
                    'id': str(r.id),
                    'name': r.name,
                    'code': r.slug,  # Use slug as code
                    'website': r.base_url,  # Use base_url as website
                }
                for r in retailers
            ]
        }

        return json_response(data)
    except Exception as e:
        return api_error(f'Error fetching retailers: {str(e)}', 500)


# ============= Price History API =============

@require_GET
def price_history(request, listing_id):
    """
    Get price history for a listing.

    Query params:
        - days: Number of days of history (default 90)
    """
    from apps.products.models import Listing
    from apps.scraping.models import SnapshotPrice

    try:
        listing = Listing.objects.get(pk=listing_id)
    except Listing.DoesNotExist:
        return api_error('Listing not found', 404)

    days = int(request.GET.get('days', 90))
    since = timezone.now() - timedelta(days=days)

    snapshots = SnapshotPrice.objects.filter(
        listing=listing,
        scraped_at__gte=since,
    ).order_by('scraped_at')

    data = {
        'success': True,
        'listing_id': str(listing_id),
        'product': listing.product.name,
        'retailer': listing.retailer.name,
        'history': [
            {
                'date': s.scraped_at.isoformat(),
                'price_final': s.price_final,
                'price_regular': s.price_regular,
                'price_promo': s.price_promo,
                'in_stock': s.in_stock,
                'rating_avg': s.rating_avg,
                'reviews_count': s.reviews_count,
            }
            for s in snapshots
        ]
    }

    return json_response(data)


# ============= Reviews API =============

@require_GET
def reviews_list(request, listing_id):
    """
    Get reviews for a listing.

    Query params:
        - rating: Filter by rating (1-5)
        - limit: Max results (default 50)
        - offset: Pagination offset
    """
    from apps.products.models import Listing
    from apps.scraping.models import ReviewItem

    try:
        listing = Listing.objects.get(pk=listing_id)
    except Listing.DoesNotExist:
        return api_error('Listing not found', 404)

    reviews = ReviewItem.objects.filter(listing=listing)

    if request.GET.get('rating'):
        reviews = reviews.filter(rating=int(request.GET.get('rating')))

    limit = min(int(request.GET.get('limit', 50)), 100)
    offset = int(request.GET.get('offset', 0))

    total = reviews.count()
    reviews = reviews.order_by('-published_at')[offset:offset + limit]

    data = {
        'success': True,
        'listing_id': str(listing_id),
        'total': total,
        'reviews': [
            {
                'id': str(r.id),
                'rating': r.rating,
                'text': r.text,
                'author': r.author_name,
                'pros': r.pros,
                'cons': r.cons,
                'published_at': r.published_at.isoformat() if r.published_at else None,
            }
            for r in reviews
        ]
    }

    return json_response(data)


# ============= Alerts API =============

@require_GET
def alerts_list(request):
    """
    Get recent alert events.

    Query params:
        - days: Number of days (default 7)
        - delivered: Filter by delivery status (true/false)
        - limit: Max results (default 50)
    """
    try:
        from apps.alerts.models import AlertEvent

        days = int(request.GET.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        events = AlertEvent.objects.filter(
            triggered_at__gte=since,
        ).select_related('alert_rule', 'listing__product', 'listing__retailer')

        if request.GET.get('delivered'):
            is_delivered = request.GET.get('delivered').lower() == 'true'
            events = events.filter(is_delivered=is_delivered)

        limit = min(int(request.GET.get('limit', 50)), 100)
        events = events.order_by('-triggered_at')[:limit]

        data = {
            'success': True,
            'events': [
                {
                    'id': str(e.id),
                    'rule_name': e.alert_rule.name,
                    'alert_type': e.alert_rule.alert_type,
                    'product': e.listing.product.name,
                    'retailer': e.listing.retailer.name,
                    'message': e.message,
                    'details': e.details,
                    'triggered_at': e.triggered_at.isoformat(),
                    'is_delivered': e.is_delivered,
                    'delivered_at': e.delivered_at.isoformat() if e.delivered_at else None,
                }
                for e in events
            ]
        }

        return json_response(data)
    except Exception as e:
        return api_error(f'Error fetching alerts: {str(e)}', 500)


# ============= Analytics API =============

@require_GET
def analytics_summary(request):
    """
    Get analytics summary for dashboard.
    """
    try:
        from apps.products.models import Product, Listing
        from apps.scraping.models import SnapshotPrice, ReviewItem, ScrapeSession
        from apps.alerts.models import AlertEvent

        week_ago = timezone.now() - timedelta(days=7)

        # Product counts (Product doesn't have is_active field)
        total_products = Product.objects.count()
        own_products = Product.objects.filter(is_own=True).count()
        competitor_products = total_products - own_products

        # Listing counts
        total_listings = Listing.objects.filter(is_active=True).count()

        # Recent activity
        recent_snapshots = SnapshotPrice.objects.filter(scraped_at__gte=week_ago).count()
        recent_reviews = ReviewItem.objects.filter(created_at__gte=week_ago).count()
        recent_alerts = AlertEvent.objects.filter(triggered_at__gte=week_ago).count()

        # Session stats
        recent_sessions = ScrapeSession.objects.filter(
            started_at__gte=week_ago,
            status=ScrapeSession.StatusChoices.COMPLETED,
        ).count()

        data = {
            'success': True,
            'summary': {
                'products': {
                    'total': total_products,
                    'own': own_products,
                    'competitors': competitor_products,
                },
                'listings': total_listings,
                'recent_activity': {
                    'snapshots_7d': recent_snapshots,
                    'reviews_7d': recent_reviews,
                    'alerts_7d': recent_alerts,
                    'sessions_7d': recent_sessions,
                }
            }
        }

        return json_response(data)
    except Exception as e:
        return api_error(f'Error fetching analytics: {str(e)}', 500)


# ============= Scraping Control API =============

@require_POST
def trigger_scrape(request):
    """
    Trigger a scraping session.

    POST body (JSON):
        - listing_id: Optional specific listing to scrape
        - retailer_id: Optional retailer filter
    """
    from apps.products.models import Listing
    from apps.retailers.models import Retailer
    from apps.scraping.models import ScrapeSession
    from apps.scraping.tasks import scrape_single_listing, run_scrape_session

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return api_error('Invalid JSON body')

    listing_id = body.get('listing_id')
    retailer_id = body.get('retailer_id')

    if listing_id:
        # Scrape single listing
        try:
            listing = Listing.objects.get(pk=listing_id, is_active=True)
        except Listing.DoesNotExist:
            return api_error('Listing not found', 404)

        scrape_single_listing.delay(str(listing.pk), user_id=request.user.id)

        return json_response({
            'success': True,
            'message': f'Scrape task queued for {listing.product.name}',
            'listing_id': str(listing_id),
        })

    else:
        # Full scrape session
        retailer = None
        if retailer_id:
            try:
                retailer = Retailer.objects.get(pk=retailer_id, is_active=True)
            except Retailer.DoesNotExist:
                return api_error('Retailer not found', 404)

        session = ScrapeSession.objects.create(
            trigger_type=ScrapeSession.TriggerChoices.MANUAL,
            retailer=retailer,
            triggered_by=request.user,
        )

        run_scrape_session.delay(str(session.pk))

        return json_response({
            'success': True,
            'message': 'Scrape session started',
            'session_id': str(session.pk),
        })


@require_GET
def scrape_status(request, session_id):
    """
    Get scrape session status.
    """
    from apps.scraping.models import ScrapeSession

    try:
        session = ScrapeSession.objects.get(pk=session_id)
    except ScrapeSession.DoesNotExist:
        return api_error('Session not found', 404)

    data = {
        'success': True,
        'session': {
            'id': str(session.id),
            'status': session.status,
            'trigger_type': session.trigger_type,
            'retailer': session.retailer.name if session.retailer else 'All',
            'listings_total': session.listings_total,
            'listings_success': session.listings_success,
            'listings_failed': session.listings_failed,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'finished_at': session.finished_at.isoformat() if session.finished_at else None,
            'error_log': session.error_log[:500] if session.error_log else None,
        }
    }

    return json_response(data)


# ============= Export API =============

@require_GET
def export_products(request):
    """
    Export products with latest prices to JSON.

    Query params:
        - format: json (default) or csv
        - is_own: Filter by own products
    """
    try:
        from apps.products.models import Product, Listing
        from apps.scraping.models import SnapshotPrice

        products = Product.objects.all()

        if request.GET.get('is_own'):
            is_own = request.GET.get('is_own').lower() == 'true'
            products = products.filter(is_own=is_own)

        export_data = []

        for product in products:
            listings = Listing.objects.filter(product=product, is_active=True)

            product_data = {
                'name': product.name,
                'brand': product.brand,
                'sku': '',  # Not in model
                'barcode': '',  # Not in model
                'is_own': product.is_own,
                'category': None,  # Not in model
                'prices': [],
            }

            for listing in listings:
                latest = SnapshotPrice.objects.filter(
                    listing=listing
                ).order_by('-scraped_at').first()

                if latest:
                    product_data['prices'].append({
                        'retailer': listing.retailer.name,
                        'url': listing.external_url,
                        'price_final': float(latest.price_final) if latest.price_final else None,
                        'price_regular': float(latest.price_regular) if latest.price_regular else None,
                        'in_stock': latest.in_stock,
                        'rating': latest.rating_avg,
                        'reviews_count': latest.reviews_count,
                        'scraped_at': latest.scraped_at.isoformat(),
                    })

            export_data.append(product_data)

        return json_response({
            'success': True,
            'exported_at': timezone.now().isoformat(),
            'product_count': len(export_data),
            'products': export_data,
        })
    except Exception as e:
        return api_error(f'Error exporting products: {str(e)}', 500)
