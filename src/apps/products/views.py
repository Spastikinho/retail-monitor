from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.shortcuts import get_object_or_404

from .models import Product, Listing
from .forms import ProductForm, ListingForm, ImportForm
from .import_export import ProductImporter, ProductExporter


class ProductListView(LoginRequiredMixin, ListView):
    """List all products with filtering."""

    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('listings__retailer')

        # Filter by is_own
        is_own = self.request.GET.get('is_own')
        if is_own == '1':
            queryset = queryset.filter(is_own=True)
        elif is_own == '0':
            queryset = queryset.filter(is_own=False)

        # Filter by brand
        brand = self.request.GET.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # Search
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Product detail with listings and history."""

    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Q
        from apps.scraping.models import SnapshotPrice, ReviewItem
        from apps.analytics.models import ReviewAnalysis

        context = super().get_context_data(**kwargs)
        context['listings'] = self.object.listings.select_related('retailer').all()

        # Get listing IDs for all queries
        listing_ids = list(self.object.listings.values_list('id', flat=True))

        # Get price history for all listings of this product
        context['price_history'] = SnapshotPrice.objects.filter(
            listing_id__in=listing_ids
        ).select_related('listing__retailer').order_by('-scraped_at')[:20]

        # Get reviews for this product
        context['reviews'] = ReviewItem.objects.filter(
            listing_id__in=listing_ids
        ).select_related('listing__retailer').order_by('-published_at', '-scraped_at')[:10]

        # Calculate review statistics
        if listing_ids:
            stats = ReviewItem.objects.filter(
                listing_id__in=listing_ids
            ).aggregate(
                total=Count('id'),
                negative=Count('id', filter=Q(rating__lte=3)),
                neutral=Count('id', filter=Q(rating=4)),
                positive=Count('id', filter=Q(rating=5)),
            )
            if stats['total'] > 0:
                context['reviews_stats'] = stats

            # Get latest AI analysis for each listing
            context['analyses'] = ReviewAnalysis.objects.filter(
                listing_id__in=listing_ids
            ).select_related('listing__retailer').order_by('-period_month')[:5]

        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Create a new product."""

    model = Product
    form_class = ProductForm
    template_name = 'products/form.html'
    success_url = reverse_lazy('products:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Добавить товар'
        context['submit_text'] = 'Создать'
        return context


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing product."""

    model = Product
    form_class = ProductForm
    template_name = 'products/form.html'

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Редактировать товар'
        context['submit_text'] = 'Сохранить'
        return context


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a product."""

    model = Product
    template_name = 'products/confirm_delete.html'
    success_url = reverse_lazy('products:list')


class ListingCreateView(LoginRequiredMixin, CreateView):
    """Add a listing to a product."""

    model = Listing
    form_class = ListingForm
    template_name = 'products/listing_form.html'

    def get_product(self):
        return get_object_or_404(Product, pk=self.kwargs['product_pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product'] = self.get_product()
        return kwargs

    def form_valid(self, form):
        form.instance.product = self.get_product()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.kwargs['product_pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.get_product()
        context['page_title'] = 'Добавить листинг'
        return context


class ListingDeleteView(LoginRequiredMixin, DeleteView):
    """Remove a listing."""

    model = Listing
    template_name = 'products/listing_confirm_delete.html'

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.object.product.pk})


class ProductImportView(LoginRequiredMixin, FormView):
    """Import products from Excel/CSV."""

    template_name = 'products/import.html'
    form_class = ImportForm
    success_url = reverse_lazy('products:list')

    def form_valid(self, form):
        file = form.cleaned_data['file']
        filename = file.name.lower()

        importer = ProductImporter()

        if filename.endswith('.xlsx'):
            result = importer.import_xlsx(file)
        elif filename.endswith('.csv'):
            result = importer.import_csv(file)
        else:
            messages.error(self.request, 'Неподдерживаемый формат файла')
            return self.form_invalid(form)

        if result.errors:
            for error in result.errors[:10]:  # Show first 10 errors
                messages.error(self.request, error)
            if len(result.errors) > 10:
                messages.warning(self.request, f'...и ещё {len(result.errors) - 10} ошибок')

        messages.success(
            self.request,
            f'Импорт завершён: товаров создано {result.products_created}, '
            f'обновлено {result.products_updated}, '
            f'листингов создано {result.listings_created}'
        )

        return super().form_valid(form)


class ProductExportView(LoginRequiredMixin, View):
    """Export products to Excel/CSV."""

    def get(self, request):
        format_type = request.GET.get('format', 'xlsx')
        exporter = ProductExporter()

        # Apply same filters as list view
        queryset = Product.objects.all()

        is_own = request.GET.get('is_own')
        if is_own == '1':
            queryset = queryset.filter(is_own=True)
        elif is_own == '0':
            queryset = queryset.filter(is_own=False)

        if format_type == 'csv':
            content = exporter.export_csv(queryset)
            response = HttpResponse(content, content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="products.csv"'
        else:
            content = exporter.export_xlsx(queryset)
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="products.xlsx"'

        return response


class BatchActionView(LoginRequiredMixin, View):
    """Handle batch actions on products."""

    def post(self, request):
        from django.shortcuts import redirect

        action = request.POST.get('action')
        product_ids = request.POST.getlist('product_ids')

        if not product_ids:
            messages.error(request, 'Не выбраны товары')
            return self.redirect_back(request)

        products = Product.objects.filter(pk__in=product_ids)
        count = products.count()

        if action == 'activate':
            products.update(is_active=True)
            messages.success(request, f'Активировано товаров: {count}')

        elif action == 'deactivate':
            products.update(is_active=False)
            messages.success(request, f'Деактивировано товаров: {count}')

        elif action == 'mark_own':
            products.update(is_own=True)
            messages.success(request, f'Отмечено как свои: {count}')

        elif action == 'mark_competitor':
            products.update(is_own=False)
            messages.success(request, f'Отмечено как конкуренты: {count}')

        elif action == 'scrape':
            from apps.scraping.tasks import scrape_single_listing
            from apps.scraping.models import ScrapeSession

            # Get all active listings for these products
            listings = Listing.objects.filter(
                product__in=products,
                is_active=True,
            )

            if listings.exists():
                session = ScrapeSession.objects.create(
                    trigger_type=ScrapeSession.TriggerChoices.MANUAL,
                    triggered_by=request.user,
                    listings_total=listings.count(),
                )

                for listing in listings:
                    scrape_single_listing.delay(
                        str(listing.pk),
                        user_id=request.user.id,
                        session_id=str(session.pk),
                    )

                messages.success(
                    request,
                    f'Запущен сбор данных для {listings.count()} листингов'
                )
            else:
                messages.warning(request, 'Нет активных листингов для выбранных товаров')

        elif action == 'delete':
            products.delete()
            messages.success(request, f'Удалено товаров: {count}')

        else:
            messages.error(request, f'Неизвестное действие: {action}')

        return self.redirect_back(request)

    def redirect_back(self, request):
        from django.shortcuts import redirect
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('products:list')
