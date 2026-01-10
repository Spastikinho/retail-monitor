"""
Analytics views - LLM analysis of reviews.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, View

from .models import ReviewAnalysis


class AnalysisListView(LoginRequiredMixin, ListView):
    """List all review analyses."""

    model = ReviewAnalysis
    template_name = 'analytics/analysis_list.html'
    context_object_name = 'analyses'
    paginate_by = 20

    def get_queryset(self):
        return ReviewAnalysis.objects.select_related(
            'listing__product', 'listing__retailer'
        ).order_by('-generated_at')


class AnalysisDetailView(LoginRequiredMixin, DetailView):
    """View analysis details."""

    model = ReviewAnalysis
    template_name = 'analytics/analysis_detail.html'
    context_object_name = 'analysis'

    def get_queryset(self):
        return ReviewAnalysis.objects.select_related(
            'listing__product', 'listing__retailer'
        )


class GenerateAnalysisView(LoginRequiredMixin, View):
    """Trigger LLM analysis generation."""

    def get(self, request):
        """Show generate analysis form."""
        from django.shortcuts import render
        from apps.products.models import Product

        products = Product.objects.filter(is_own=True, is_active=True)
        return render(request, 'analytics/generate.html', {
            'products': products,
            'page_title': 'Запустить анализ',
        })

    def post(self, request):
        """Start analysis generation task."""
        try:
            from .tasks import run_analysis_for_all_listings
            result = run_analysis_for_all_listings.delay()
            messages.success(
                request,
                f'Анализ запущен. ID задачи: {result.id}'
            )
        except Exception as e:
            messages.error(request, f'Ошибка запуска анализа: {e}')

        return redirect('analytics:analysis_list')
