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


@csrf_exempt
@require_POST
def setup_retailers(request):
    """
    Initialize retailers in the database.
    Call this once to set up the system.
    """
    from apps.retailers.models import Retailer

    retailers_data = [
        {
            'name': 'Ozon',
            'slug': 'ozon',
            'base_url': 'https://www.ozon.ru',
            'connector_class': 'apps.scraping.connectors.ozon.OzonConnector',
            'product_url_pattern': r'ozon\.ru/product/[^/]+-(\d+)',
            'requires_auth': False,
            'rate_limit_rpm': 10,
        },
        {
            'name': 'Wildberries',
            'slug': 'wildberries',
            'base_url': 'https://www.wildberries.ru',
            'connector_class': 'apps.scraping.connectors.wildberries.WildberriesConnector',
            'product_url_pattern': r'wildberries\.ru/catalog/(\d+)/detail',
            'requires_auth': False,
            'rate_limit_rpm': 10,
        },
        {
            'name': 'ВкусВилл',
            'slug': 'vkusvill',
            'base_url': 'https://vkusvill.ru',
            'connector_class': 'apps.scraping.connectors.vkusvill.VkusvillConnector',
            'product_url_pattern': r'vkusvill\.ru/goods/[^/]+-(\d+)\.html',
            'requires_auth': False,
            'rate_limit_rpm': 10,
        },
        {
            'name': 'Перекрёсток',
            'slug': 'perekrestok',
            'base_url': 'https://www.perekrestok.ru',
            'connector_class': 'apps.scraping.connectors.perekrestok.PerekrestokConnector',
            'product_url_pattern': r'perekrestok\.ru/cat/\d+/p/[^/]+-(\d+)',
            'requires_auth': False,
            'rate_limit_rpm': 10,
        },
        {
            'name': 'Яндекс Лавка',
            'slug': 'lavka',
            'base_url': 'https://lavka.yandex.ru',
            'connector_class': 'apps.scraping.connectors.lavka.LavkaConnector',
            'product_url_pattern': r'lavka\.yandex\.ru/product/([a-zA-Z0-9_-]+)',
            'requires_auth': False,
            'rate_limit_rpm': 5,
        },
    ]

    created = []
    updated = []
    for data in retailers_data:
        retailer, was_created = Retailer.objects.update_or_create(
            slug=data['slug'],
            defaults=data,
        )
        if was_created:
            created.append(retailer.name)
        else:
            updated.append(retailer.name)

    return json_response({
        'success': True,
        'message': f'Created {len(created)}, updated {len(updated)} retailers',
        'created': created,
        'updated': updated,
    })


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


# ============= Manual Import API =============

@csrf_exempt
@require_POST
def import_urls(request):
    """
    Import URLs for scraping.

    POST body (JSON):
        - urls: List of URLs to import (max 20)
        - product_type: 'own' or 'competitor' (default: 'competitor')
        - group_id: Optional monitoring group ID
    """
    try:
        from apps.scraping.models import ManualImport, MonitoringGroup
        from apps.scraping.tasks import process_manual_import

        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return api_error('Invalid JSON body')

        urls = body.get('urls', [])
        product_type = body.get('product_type', 'competitor')
        group_id = body.get('group_id')

        if not urls:
            return api_error('No URLs provided')

        if len(urls) > 20:
            return api_error('Maximum 20 URLs per request')

        # Validate product_type
        if product_type not in ['own', 'competitor']:
            product_type = 'competitor'

        # Get group if specified
        group = None
        if group_id:
            try:
                group = MonitoringGroup.objects.get(pk=group_id)
            except MonitoringGroup.DoesNotExist:
                pass

        # Get or create a default user for API imports
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = request.user if request.user.is_authenticated else User.objects.first()

        if not user:
            # Auto-create a default user for API imports
            user = User.objects.create_user(
                username='api_user',
                email='api@retailmonitor.local',
                password=User.objects.make_random_password()
            )

        created_imports = []
        errors = []

        for url in urls:
            url = url.strip()
            if not url:
                continue

            # Check for supported retailers
            supported = False
            for pattern in ['ozon.ru', 'wildberries.ru', 'wb.ru', 'perekrestok.ru',
                           'vkusvill.ru', 'lavka.yandex.ru', 'eda.yandex.ru/lavka']:
                if pattern in url.lower():
                    supported = True
                    break

            if not supported:
                errors.append(f'Unsupported retailer: {url[:50]}')
                continue

            try:
                import_obj = ManualImport.objects.create(
                    user=user,
                    url=url,
                    product_type=product_type,
                    group=group,
                )
                created_imports.append({
                    'id': str(import_obj.id),
                    'url': url,
                    'retailer': import_obj.retailer.name if import_obj.retailer else None,
                    'status': import_obj.status,
                })

                # Queue for processing (optional - may fail if Redis not available)
                try:
                    process_manual_import.delay(str(import_obj.pk))
                except Exception as task_err:
                    # Celery/Redis not available - import saved but not processed
                    errors.append(f'Import saved but processing queued failed: {str(task_err)[:50]}')

            except Exception as e:
                errors.append(f'Error creating import for {url[:30]}: {str(e)}')

        return json_response({
            'success': True,
            'message': f'Created {len(created_imports)} imports',
            'imports': created_imports,
            'errors': errors,
        })

    except Exception as e:
        return api_error(f'Error importing URLs: {str(e)}', 500)


@require_GET
def import_list(request):
    """
    List manual imports with optional filtering.

    Query params:
        - status: Filter by status (pending, processing, completed, failed)
        - product_type: Filter by type (own, competitor)
        - period: Filter by period (YYYY-MM)
        - limit: Max results (default 50)
        - offset: Pagination offset
    """
    try:
        from apps.scraping.models import ManualImport

        imports = ManualImport.objects.all().select_related('retailer', 'group')

        # Apply filters
        if request.GET.get('status'):
            imports = imports.filter(status=request.GET.get('status'))

        if request.GET.get('product_type'):
            imports = imports.filter(product_type=request.GET.get('product_type'))

        if request.GET.get('period'):
            try:
                from datetime import datetime
                period = datetime.strptime(request.GET.get('period'), '%Y-%m').date()
                imports = imports.filter(monitoring_period=period.replace(day=1))
            except ValueError:
                pass

        # Pagination
        limit = min(int(request.GET.get('limit', 50)), 100)
        offset = int(request.GET.get('offset', 0))

        total = imports.count()
        imports = imports.order_by('-created_at')[offset:offset + limit]

        data = {
            'success': True,
            'total': total,
            'imports': [
                {
                    'id': str(imp.id),
                    'url': imp.url,
                    'retailer': imp.retailer.name if imp.retailer else None,
                    'product_type': imp.product_type,
                    'product_title': imp.product_title,
                    'custom_name': imp.custom_name,
                    'status': imp.status,
                    'price_final': float(imp.price_final) if imp.price_final else None,
                    'price_change': float(imp.price_change) if imp.price_change else None,
                    'price_change_pct': float(imp.price_change_pct) if imp.price_change_pct else None,
                    'rating': float(imp.rating) if imp.rating else None,
                    'reviews_count': imp.reviews_count,
                    'in_stock': imp.in_stock,
                    'reviews_positive': imp.reviews_positive_count,
                    'reviews_negative': imp.reviews_negative_count,
                    'monitoring_period': imp.monitoring_period.isoformat() if imp.monitoring_period else None,
                    'created_at': imp.created_at.isoformat(),
                    'processed_at': imp.processed_at.isoformat() if imp.processed_at else None,
                    'error_message': imp.error_message if imp.status == 'failed' else None,
                }
                for imp in imports
            ]
        }

        return json_response(data)

    except Exception as e:
        return api_error(f'Error fetching imports: {str(e)}', 500)


@require_GET
def import_detail(request, import_id):
    """Get detailed import info including reviews."""
    try:
        from apps.scraping.models import ManualImport

        try:
            imp = ManualImport.objects.select_related('retailer', 'group').get(pk=import_id)
        except ManualImport.DoesNotExist:
            return api_error('Import not found', 404)

        data = {
            'success': True,
            'import': {
                'id': str(imp.id),
                'url': imp.url,
                'retailer': imp.retailer.name if imp.retailer else None,
                'product_type': imp.product_type,
                'product_title': imp.product_title,
                'custom_name': imp.custom_name,
                'notes': imp.notes,
                'status': imp.status,
                'price_regular': float(imp.price_regular) if imp.price_regular else None,
                'price_promo': float(imp.price_promo) if imp.price_promo else None,
                'price_final': float(imp.price_final) if imp.price_final else None,
                'price_previous': float(imp.price_previous) if imp.price_previous else None,
                'price_change': float(imp.price_change) if imp.price_change else None,
                'price_change_pct': float(imp.price_change_pct) if imp.price_change_pct else None,
                'rating': float(imp.rating) if imp.rating else None,
                'reviews_count': imp.reviews_count,
                'in_stock': imp.in_stock,
                'reviews_positive': imp.reviews_positive_count,
                'reviews_negative': imp.reviews_negative_count,
                'reviews_neutral': imp.reviews_neutral_count,
                'review_insights': imp.review_insights,
                'reviews_data': imp.reviews_data[:50] if imp.reviews_data else [],
                'monitoring_period': imp.monitoring_period.isoformat() if imp.monitoring_period else None,
                'is_recurring': imp.is_recurring,
                'group': {
                    'id': str(imp.group.id),
                    'name': imp.group.name,
                } if imp.group else None,
                'created_at': imp.created_at.isoformat(),
                'processed_at': imp.processed_at.isoformat() if imp.processed_at else None,
                'error_message': imp.error_message,
            }
        }

        return json_response(data)

    except Exception as e:
        return api_error(f'Error fetching import: {str(e)}', 500)


# ============= Monitoring Groups API =============

@require_GET
def monitoring_groups_list(request):
    """List monitoring groups."""
    try:
        from apps.scraping.models import MonitoringGroup

        groups = MonitoringGroup.objects.all()

        data = {
            'success': True,
            'groups': [
                {
                    'id': str(g.id),
                    'name': g.name,
                    'description': g.description,
                    'group_type': g.group_type,
                    'color': g.color,
                    'imports_count': g.imports.count(),
                }
                for g in groups
            ]
        }

        return json_response(data)

    except Exception as e:
        return api_error(f'Error fetching groups: {str(e)}', 500)


@csrf_exempt
@require_http_methods(['POST', 'PUT'])
def monitoring_group_create(request):
    """Create or update a monitoring group."""
    try:
        from apps.scraping.models import MonitoringGroup
        from django.contrib.auth import get_user_model

        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return api_error('Invalid JSON body')

        name = body.get('name')
        if not name:
            return api_error('Name is required')

        User = get_user_model()
        user = request.user if request.user.is_authenticated else User.objects.first()

        if not user:
            return api_error('No user available', 500)

        group_id = body.get('id')

        if group_id:
            try:
                group = MonitoringGroup.objects.get(pk=group_id)
                group.name = name
                group.description = body.get('description', group.description)
                group.group_type = body.get('group_type', group.group_type)
                group.color = body.get('color', group.color)
                group.save()
            except MonitoringGroup.DoesNotExist:
                return api_error('Group not found', 404)
        else:
            group = MonitoringGroup.objects.create(
                user=user,
                name=name,
                description=body.get('description', ''),
                group_type=body.get('group_type', 'own'),
                color=body.get('color', '#3B82F6'),
            )

        return json_response({
            'success': True,
            'group': {
                'id': str(group.id),
                'name': group.name,
                'description': group.description,
                'group_type': group.group_type,
                'color': group.color,
            }
        })

    except Exception as e:
        return api_error(f'Error saving group: {str(e)}', 500)


# ============= Excel Export API =============

@require_GET
def export_monitoring_excel(request):
    """
    Export monitoring data to Excel.

    Query params:
        - period: Filter by period (YYYY-MM)

    Returns Excel file download.
    """
    try:
        from django.http import HttpResponse
        from apps.scraping.exports import export_imports_to_excel
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = request.user if request.user.is_authenticated else User.objects.first()

        if not user:
            return api_error('No user available', 500)

        # Parse period
        period = None
        if request.GET.get('period'):
            try:
                from datetime import datetime
                period = datetime.strptime(request.GET.get('period'), '%Y-%m').date()
            except ValueError:
                pass

        # Generate Excel
        buffer = export_imports_to_excel(user, period)

        # Create response
        filename = f'monitoring_{period.strftime("%Y-%m") if period else "all"}.xlsx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return api_error(f'Error exporting Excel: {str(e)}', 500)


@require_GET
def export_import_excel(request, import_id):
    """
    Export single import to Excel.

    Returns Excel file download.
    """
    try:
        from django.http import HttpResponse
        from apps.scraping.models import ManualImport
        from apps.scraping.exports import export_single_import_to_excel

        try:
            imp = ManualImport.objects.get(pk=import_id)
        except ManualImport.DoesNotExist:
            return api_error('Import not found', 404)

        # Generate Excel
        buffer = export_single_import_to_excel(imp)

        # Create response
        name = (imp.custom_name or imp.product_title or 'product')[:30]
        filename = f'{name}_{imp.created_at.strftime("%Y%m%d")}.xlsx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return api_error(f'Error exporting Excel: {str(e)}', 500)


# ============= Available Periods API =============

@require_GET
def available_periods(request):
    """Get list of available monitoring periods."""
    try:
        from apps.scraping.models import ManualImport

        periods = ManualImport.objects.filter(
            status=ManualImport.StatusChoices.COMPLETED,
            monitoring_period__isnull=False,
        ).values('monitoring_period').annotate(
            count=Count('id')
        ).order_by('-monitoring_period')

        data = {
            'success': True,
            'periods': [
                {
                    'period': p['monitoring_period'].isoformat(),
                    'label': p['monitoring_period'].strftime('%B %Y'),
                    'count': p['count'],
                }
                for p in periods
            ]
        }

        return json_response(data)

    except Exception as e:
        return api_error(f'Error fetching periods: {str(e)}', 500)


# ============= Runs API (Batch Import with Status Tracking) =============

@csrf_exempt
@require_POST
def create_run(request):
    """
    Create a new scraping run with multiple URLs.

    POST body (JSON):
        - items: List of { url: string, retailer?: string, name?: string }
        - options: { product_type?: 'own'|'competitor', group_id?: string, scrape_reviews?: bool }

    Returns:
        - run_id: UUID for tracking the batch
        - created_at: Timestamp
        - items_count: Number of items queued
    """
    try:
        from apps.scraping.models import ManualImport, MonitoringGroup, ScrapeRun
        from apps.scraping.tasks import process_manual_import
        from django.contrib.auth import get_user_model

        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return api_error('Invalid JSON body')

        items = body.get('items', [])
        options = body.get('options', {})

        if not items:
            return api_error('No items provided')

        if len(items) > 50:
            return api_error('Maximum 50 items per run')

        # Get or create user
        User = get_user_model()
        user = request.user if request.user.is_authenticated else User.objects.first()

        if not user:
            user = User.objects.create_user(
                username='api_user',
                email='api@retailmonitor.local',
                password=User.objects.make_random_password()
            )

        # Parse options
        product_type = options.get('product_type', 'competitor')
        if product_type not in ['own', 'competitor']:
            product_type = 'competitor'

        scrape_reviews = options.get('scrape_reviews', True)

        group = None
        if options.get('group_id'):
            try:
                group = MonitoringGroup.objects.get(pk=options['group_id'])
            except MonitoringGroup.DoesNotExist:
                pass

        # Create ScrapeRun to track the batch
        run = ScrapeRun.objects.create(
            user=user,
            items_total=len(items),
            options={
                'product_type': product_type,
                'scrape_reviews': scrape_reviews,
                'group_id': str(group.id) if group else None,
            }
        )

        # Create ManualImport for each item
        created_imports = []
        errors = []

        for item in items:
            url = item.get('url', '').strip()
            if not url:
                errors.append({'url': '', 'error': 'Empty URL'})
                continue

            # Check for supported retailers
            supported = False
            for pattern in ['ozon.ru', 'wildberries.ru', 'wb.ru', 'perekrestok.ru',
                           'vkusvill.ru', 'lavka.yandex.ru', 'eda.yandex.ru/lavka']:
                if pattern in url.lower():
                    supported = True
                    break

            if not supported:
                errors.append({'url': url[:50], 'error': 'Unsupported retailer'})
                run.items_failed += 1
                run.save(update_fields=['items_failed'])
                continue

            try:
                import_obj = ManualImport.objects.create(
                    user=user,
                    url=url,
                    product_type=product_type,
                    group=group,
                    custom_name=item.get('name', ''),
                    run=run,  # Link to run
                )
                created_imports.append(str(import_obj.id))

                # Queue for processing
                try:
                    process_manual_import.delay(str(import_obj.pk), scrape_reviews=scrape_reviews)
                except Exception as task_err:
                    errors.append({'url': url[:50], 'error': f'Queue failed: {str(task_err)[:30]}'})

            except Exception as e:
                errors.append({'url': url[:50], 'error': str(e)[:50]})
                run.items_failed += 1
                run.save(update_fields=['items_failed'])

        # Update run status
        if created_imports:
            run.status = 'processing'
        elif errors:
            run.status = 'failed'
        run.save()

        return json_response({
            'success': True,
            'run_id': str(run.id),
            'created_at': run.created_at.isoformat(),
            'items_count': len(created_imports),
            'errors': errors if errors else None,
        })

    except Exception as e:
        return api_error(f'Error creating run: {str(e)}', 500)


@require_GET
def get_run(request, run_id):
    """
    Get run status and results.

    Returns:
        - run_id, status, progress
        - results: List of completed items with data
        - errors: List of failed items with error messages
    """
    try:
        from apps.scraping.models import ScrapeRun, ManualImport

        try:
            run = ScrapeRun.objects.get(pk=run_id)
        except ScrapeRun.DoesNotExist:
            return api_error('Run not found', 404)

        # Get all imports for this run
        imports = ManualImport.objects.filter(run=run).order_by('created_at')

        # Calculate progress
        completed = imports.filter(status='completed').count()
        failed = imports.filter(status='failed').count()
        processing = imports.filter(status__in=['pending', 'processing']).count()

        # Update run stats
        run.items_completed = completed
        run.items_failed = failed

        if processing == 0 and (completed > 0 or failed > 0):
            run.status = 'completed' if failed == 0 else 'completed_with_errors'
            run.finished_at = timezone.now()

        run.save()

        # Build results and errors lists
        results = []
        errors = []

        for imp in imports:
            if imp.status == 'completed':
                results.append({
                    'id': str(imp.id),
                    'url': imp.url,
                    'retailer': imp.retailer.name if imp.retailer else None,
                    'product_title': imp.product_title,
                    'custom_name': imp.custom_name,
                    'price': {
                        'regular': float(imp.price_regular) if imp.price_regular else None,
                        'promo': float(imp.price_promo) if imp.price_promo else None,
                        'final': float(imp.price_final) if imp.price_final else None,
                        'change': float(imp.price_change) if imp.price_change else None,
                        'change_pct': float(imp.price_change_pct) if imp.price_change_pct else None,
                    },
                    'rating': float(imp.rating) if imp.rating else None,
                    'reviews_count': imp.reviews_count,
                    'in_stock': imp.in_stock,
                    'reviews_summary': {
                        'positive': imp.reviews_positive_count,
                        'negative': imp.reviews_negative_count,
                        'neutral': imp.reviews_neutral_count,
                    } if imp.reviews_data else None,
                    'processed_at': imp.processed_at.isoformat() if imp.processed_at else None,
                })
            elif imp.status == 'failed':
                errors.append({
                    'id': str(imp.id),
                    'url': imp.url,
                    'error': imp.error_message,
                })

        # Calculate overall progress percentage
        total = run.items_total or 1
        progress_pct = int((completed + failed) / total * 100)

        return json_response({
            'success': True,
            'run': {
                'id': str(run.id),
                'status': run.status,
                'created_at': run.created_at.isoformat(),
                'finished_at': run.finished_at.isoformat() if run.finished_at else None,
                'progress': {
                    'total': run.items_total,
                    'completed': completed,
                    'failed': failed,
                    'processing': processing,
                    'percent': progress_pct,
                },
            },
            'results': results,
            'errors': errors,
        })

    except Exception as e:
        return api_error(f'Error fetching run: {str(e)}', 500)


@require_GET
def list_runs(request):
    """
    List recent runs.

    Query params:
        - status: Filter by status
        - limit: Max results (default 20)
        - offset: Pagination offset
    """
    try:
        from apps.scraping.models import ScrapeRun

        runs = ScrapeRun.objects.all()

        if request.GET.get('status'):
            runs = runs.filter(status=request.GET.get('status'))

        limit = min(int(request.GET.get('limit', 20)), 100)
        offset = int(request.GET.get('offset', 0))

        total = runs.count()
        runs = runs.order_by('-created_at')[offset:offset + limit]

        return json_response({
            'success': True,
            'total': total,
            'runs': [
                {
                    'id': str(r.id),
                    'status': r.status,
                    'items_total': r.items_total,
                    'items_completed': r.items_completed,
                    'items_failed': r.items_failed,
                    'created_at': r.created_at.isoformat(),
                    'finished_at': r.finished_at.isoformat() if r.finished_at else None,
                }
                for r in runs
            ]
        })

    except Exception as e:
        return api_error(f'Error listing runs: {str(e)}', 500)
