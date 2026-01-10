from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.http import JsonResponse, HttpResponse

from apps.products.models import Product, Listing
from apps.retailers.models import Retailer
from .models import ScrapeSession, ReviewItem, ManualImport, MonitoringGroup
from .forms import ManualImportForm, SingleUrlForm, EnhancedImportForm, MonitoringGroupForm
from .tasks import run_scrape_session, scrape_single_listing, process_manual_import
from .exports import export_imports_to_excel, export_single_import_to_excel


class ScrapeSessionListView(LoginRequiredMixin, ListView):
    """List all scrape sessions."""

    model = ScrapeSession
    template_name = 'scraping/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20


class ScrapeSessionDetailView(LoginRequiredMixin, DetailView):
    """Scrape session details."""

    model = ScrapeSession
    template_name = 'scraping/session_detail.html'
    context_object_name = 'session'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['price_snapshots'] = self.object.price_snapshots.select_related(
            'listing__product', 'listing__retailer'
        )[:50]
        return context


class RunScrapeView(LoginRequiredMixin, View):
    """Trigger a scrape run."""

    def post(self, request, listing_pk=None):
        if listing_pk:
            # Scrape single listing
            listing = get_object_or_404(Listing, pk=listing_pk)
            scrape_single_listing.delay(str(listing.pk), user_id=request.user.id)
            messages.success(
                request,
                f'Запущен сбор данных для "{listing.product.name}" на {listing.retailer.name}'
            )
            return redirect('products:detail', pk=listing.product.pk)
        else:
            # Scrape all active listings
            session = ScrapeSession.objects.create(
                trigger_type=ScrapeSession.TriggerChoices.MANUAL,
                triggered_by=request.user,
            )
            run_scrape_session.delay(str(session.pk))
            messages.success(request, 'Запущен полный сбор данных по всем товарам')
            return redirect('scraping:session_detail', pk=session.pk)


class ReviewListView(LoginRequiredMixin, ListView):
    """List all reviews with filtering."""

    model = ReviewItem
    template_name = 'scraping/reviews_list.html'
    context_object_name = 'reviews'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'listing__product', 'listing__retailer'
        ).order_by('-published_at', '-scraped_at')

        # Filter by product
        product_id = self.request.GET.get('product')
        if product_id:
            queryset = queryset.filter(listing__product_id=product_id)

        # Filter by retailer
        retailer_id = self.request.GET.get('retailer')
        if retailer_id:
            queryset = queryset.filter(listing__retailer_id=retailer_id)

        # Filter by sentiment
        sentiment = self.request.GET.get('sentiment')
        if sentiment in ('positive', 'neutral', 'negative'):
            queryset = queryset.filter(sentiment=sentiment)

        # Filter by rating
        rating = self.request.GET.get('rating')
        if rating and rating.isdigit():
            queryset = queryset.filter(rating=int(rating))

        # Filter by is_own
        is_own = self.request.GET.get('is_own')
        if is_own == '1':
            queryset = queryset.filter(listing__product__is_own=True)
        elif is_own == '0':
            queryset = queryset.filter(listing__product__is_own=False)

        # Text search
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(text__icontains=search) |
                Q(pros__icontains=search) |
                Q(cons__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filters for template
        context['products'] = Product.objects.all().order_by('name')
        context['retailers'] = Retailer.objects.filter(is_active=True).order_by('name')
        context['sentiments'] = [
            ('negative', 'Негативные'),
            ('neutral', 'Нейтральные'),
            ('positive', 'Позитивные'),
        ]
        context['ratings'] = [1, 2, 3, 4, 5]

        # Current filter values
        context['current_product'] = self.request.GET.get('product', '')
        context['current_retailer'] = self.request.GET.get('retailer', '')
        context['current_sentiment'] = self.request.GET.get('sentiment', '')
        context['current_rating'] = self.request.GET.get('rating', '')
        context['current_is_own'] = self.request.GET.get('is_own', '')
        context['current_search'] = self.request.GET.get('q', '')

        return context


class ReviewDetailView(LoginRequiredMixin, DetailView):
    """Single review detail."""

    model = ReviewItem
    template_name = 'scraping/review_detail.html'
    context_object_name = 'review'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'listing__product', 'listing__retailer'
        )


# ============================================
# Manual Import Views
# ============================================

class ManualImportCreateView(LoginRequiredMixin, CreateView):
    """Create new manual import (batch URLs)."""

    model = ManualImport
    form_class = ManualImportForm
    template_name = 'scraping/manual_import.html'
    success_url = reverse_lazy('scraping:import_list')

    def form_valid(self, form):
        urls = form.cleaned_data['urls']
        scrape_reviews = form.cleaned_data.get('scrape_reviews', True)

        # Create an import record for each URL
        created_imports = []
        for url in urls:
            import_obj = ManualImport.objects.create(
                user=self.request.user,
                url=url,
            )
            created_imports.append(import_obj)
            # Queue processing task
            process_manual_import.delay(
                str(import_obj.pk),
                scrape_reviews=scrape_reviews
            )

        messages.success(
            self.request,
            f'Добавлено {len(created_imports)} ссылок для обработки. '
            'Результаты появятся в течение нескольких минут.'
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_imports'] = ManualImport.objects.filter(
            user=self.request.user
        )[:10]
        return context


class ManualImportListView(LoginRequiredMixin, ListView):
    """List user's manual imports."""

    model = ManualImport
    template_name = 'scraping/import_list.html'
    context_object_name = 'imports'
    paginate_by = 25

    def get_queryset(self):
        return ManualImport.objects.filter(
            user=self.request.user
        ).select_related('retailer').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats
        qs = self.get_queryset()
        context['total_count'] = qs.count()
        context['pending_count'] = qs.filter(status='pending').count()
        context['processing_count'] = qs.filter(status='processing').count()
        context['completed_count'] = qs.filter(status='completed').count()
        context['failed_count'] = qs.filter(status='failed').count()
        return context


class ManualImportDetailView(LoginRequiredMixin, DetailView):
    """View manual import result details."""

    model = ManualImport
    template_name = 'scraping/import_detail.html'
    context_object_name = 'import_obj'

    def get_queryset(self):
        return ManualImport.objects.filter(
            user=self.request.user
        ).select_related('retailer')


class ManualImportStatusView(LoginRequiredMixin, View):
    """AJAX endpoint to check import status."""

    def get(self, request, pk):
        import_obj = get_object_or_404(
            ManualImport,
            pk=pk,
            user=request.user
        )

        return JsonResponse({
            'id': str(import_obj.pk),
            'status': import_obj.status,
            'status_display': import_obj.get_status_display(),
            'product_title': import_obj.product_title,
            'price_final': float(import_obj.price_final) if import_obj.price_final else None,
            'rating': float(import_obj.rating) if import_obj.rating else None,
            'reviews_count': import_obj.reviews_count,
            'in_stock': import_obj.in_stock,
            'error_message': import_obj.error_message,
            'processed_at': import_obj.processed_at.isoformat() if import_obj.processed_at else None,
        })


class QuickImportView(LoginRequiredMixin, View):
    """Quick single URL import via AJAX."""

    def post(self, request):
        form = SingleUrlForm(request.POST)

        if form.is_valid():
            url = form.cleaned_data['url']

            import_obj = ManualImport.objects.create(
                user=request.user,
                url=url,
            )
            # Queue processing
            process_manual_import.delay(str(import_obj.pk), scrape_reviews=True)

            return JsonResponse({
                'success': True,
                'import_id': str(import_obj.pk),
                'message': 'Обработка начата',
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)


class ManualImportDeleteView(LoginRequiredMixin, View):
    """Delete a manual import."""

    def post(self, request, pk):
        import_obj = get_object_or_404(
            ManualImport,
            pk=pk,
            user=request.user
        )
        import_obj.delete()
        messages.success(request, 'Запись удалена')
        return redirect('scraping:import_list')


# ============================================
# Enhanced Import with Categorization
# ============================================

class EnhancedImportView(LoginRequiredMixin, CreateView):
    """Enhanced import with product categorization and monitoring options."""

    model = ManualImport
    form_class = EnhancedImportForm
    template_name = 'scraping/enhanced_import.html'
    success_url = reverse_lazy('scraping:import_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        urls = form.cleaned_data['urls']
        product_type = form.cleaned_data['product_type']
        group = form.cleaned_data.get('group')
        is_recurring = form.cleaned_data.get('is_recurring', False)
        scrape_reviews = form.cleaned_data.get('scrape_reviews', True)
        custom_name = form.cleaned_data.get('custom_name', '')

        created_imports = []
        for url in urls:
            import_obj = ManualImport.objects.create(
                user=self.request.user,
                url=url,
                product_type=product_type,
                group=group,
                is_recurring=is_recurring,
                custom_name=custom_name if len(urls) == 1 else '',
            )
            created_imports.append(import_obj)
            process_manual_import.delay(
                str(import_obj.pk),
                scrape_reviews=scrape_reviews
            )

        messages.success(
            self.request,
            f'Добавлено {len(created_imports)} товаров для мониторинга. '
            'Данные будут собраны в течение нескольких минут.'
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = MonitoringGroup.objects.filter(user=self.request.user)
        context['recent_imports'] = ManualImport.objects.filter(
            user=self.request.user
        ).select_related('group', 'retailer')[:10]
        return context


# ============================================
# Monitoring Groups
# ============================================

class MonitoringGroupListView(LoginRequiredMixin, ListView):
    """List user's monitoring groups."""

    model = MonitoringGroup
    template_name = 'scraping/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return MonitoringGroup.objects.filter(
            user=self.request.user
        ).annotate(
            imports_count=Count('imports')
        ).order_by('group_type', 'name')


class MonitoringGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new monitoring group."""

    model = MonitoringGroup
    form_class = MonitoringGroupForm
    template_name = 'scraping/group_form.html'
    success_url = reverse_lazy('scraping:group_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Группа создана')
        return super().form_valid(form)


class MonitoringGroupDeleteView(LoginRequiredMixin, View):
    """Delete a monitoring group."""

    def post(self, request, pk):
        group = get_object_or_404(
            MonitoringGroup,
            pk=pk,
            user=request.user
        )
        group.delete()
        messages.success(request, 'Группа удалена')
        return redirect('scraping:group_list')


# ============================================
# Analytics Views
# ============================================

class MonitoringAnalyticsView(LoginRequiredMixin, TemplateView):
    """Analytics dashboard for monitoring data."""

    template_name = 'scraping/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get period from query params or use current month
        period_str = self.request.GET.get('period')
        if period_str:
            try:
                period = datetime.strptime(period_str, '%Y-%m').date().replace(day=1)
            except ValueError:
                period = datetime.now().date().replace(day=1)
        else:
            period = datetime.now().date().replace(day=1)

        context['current_period'] = period

        # Get imports for this period
        imports = ManualImport.objects.filter(
            user=self.request.user,
            status=ManualImport.StatusChoices.COMPLETED,
            monitoring_period=period,
        ).select_related('retailer', 'group')

        # Own products stats
        own_products = imports.filter(product_type='own')
        context['own_count'] = own_products.count()
        context['own_with_price_increase'] = own_products.filter(price_change__gt=0)
        context['own_with_negative_reviews'] = own_products.filter(reviews_negative_count__gt=0)

        # Competitor stats
        competitors = imports.filter(product_type='competitor')
        context['competitor_count'] = competitors.count()
        context['competitor_with_price_increase'] = competitors.filter(price_change__gt=0)
        context['competitor_top_rated'] = competitors.order_by('-rating')[:5]

        # Price changes summary
        context['price_increases'] = imports.filter(price_change__gt=0).order_by('-price_change_pct')[:10]
        context['price_decreases'] = imports.filter(price_change__lt=0).order_by('price_change_pct')[:10]

        # Review insights for own products
        context['negative_feedback'] = []
        for imp in own_products.filter(reviews_negative_count__gt=0):
            insights = imp.review_insights or {}
            topics = insights.get('topics', {})
            for topic_key, topic_name in [('taste', 'Вкус'), ('packaging', 'Упаковка'),
                                          ('quality', 'Качество'), ('price', 'Цена')]:
                neg_count = topics.get(topic_key, {}).get('negative', 0)
                if neg_count > 0:
                    context['negative_feedback'].append({
                        'product': imp.display_name,
                        'topic': topic_name,
                        'count': neg_count,
                        'samples': topics.get(topic_key, {}).get('samples', [])[:1],
                    })

        # Positive insights from competitors
        context['competitor_insights'] = []
        for imp in competitors.filter(reviews_positive_count__gt=0).order_by('-rating')[:5]:
            insights = imp.review_insights or {}
            topics = insights.get('topics', {})
            for topic_key, topic_name in [('taste', 'Вкус'), ('packaging', 'Упаковка'),
                                          ('quality', 'Качество')]:
                pos_count = topics.get(topic_key, {}).get('positive', 0)
                if pos_count > 0:
                    context['competitor_insights'].append({
                        'product': imp.display_name,
                        'topic': topic_name,
                        'count': pos_count,
                        'samples': topics.get(topic_key, {}).get('samples', [])[:1],
                    })

        # Available periods
        context['available_periods'] = ManualImport.objects.filter(
            user=self.request.user,
            monitoring_period__isnull=False,
        ).values_list('monitoring_period', flat=True).distinct().order_by('-monitoring_period')

        return context


# ============================================
# Export Views
# ============================================

class ExportMonitoringView(LoginRequiredMixin, View):
    """Export all monitoring data to Excel."""

    def get(self, request):
        # Get period from query params
        period_str = request.GET.get('period')
        if period_str:
            try:
                period = datetime.strptime(period_str, '%Y-%m').date().replace(day=1)
            except ValueError:
                period = None
        else:
            period = datetime.now().date().replace(day=1)

        # Generate export
        buffer = export_imports_to_excel(request.user, period)

        # Prepare response
        filename = f'monitoring_{period.strftime("%Y-%m") if period else "all"}.xlsx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportSingleImportView(LoginRequiredMixin, View):
    """Export single import with reviews to Excel."""

    def get(self, request, pk):
        import_obj = get_object_or_404(
            ManualImport,
            pk=pk,
            user=request.user
        )

        buffer = export_single_import_to_excel(import_obj)

        # Create filename from product name
        name = import_obj.custom_name or import_obj.product_title or 'product'
        safe_name = ''.join(c for c in name if c.isalnum() or c in ' -_')[:30]
        filename = f'{safe_name}_{import_obj.created_at.strftime("%Y%m%d")}.xlsx'

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
