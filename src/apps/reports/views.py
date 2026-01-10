"""
Report views - generate and download XLSX reports.
"""
import logging
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from dateutil.relativedelta import relativedelta

from apps.products.models import Product
from apps.retailers.models import Retailer
from .export_service import ReportExporter

logger = logging.getLogger(__name__)


class ReportsIndexView(LoginRequiredMixin, TemplateView):
    """Reports index page with export options."""

    template_name = 'reports/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Date range defaults
        today = date.today()
        six_months_ago = today - relativedelta(months=6)

        context['period_from'] = six_months_ago.strftime('%Y-%m-%d')
        context['period_to'] = today.strftime('%Y-%m-%d')

        # Filter options
        context['retailers'] = Retailer.objects.filter(is_active=True).order_by('name')

        # Stats for display
        context['total_products'] = Product.objects.count()
        context['own_products'] = Product.objects.filter(is_own=True).count()
        context['competitor_products'] = Product.objects.filter(is_own=False).count()

        return context


class ExportReportView(LoginRequiredMixin, View):
    """Generate and download XLSX report."""

    def get(self, request):
        # Parse parameters
        report_type = request.GET.get('type', 'full')
        period_from = self._parse_date(request.GET.get('period_from'))
        period_to = self._parse_date(request.GET.get('period_to'))
        is_own = self._parse_is_own(request.GET.get('is_own'))
        retailer_id = request.GET.get('retailer') or None

        # Create exporter
        exporter = ReportExporter(
            period_from=period_from,
            period_to=period_to,
            is_own=is_own,
            retailer_id=retailer_id,
        )

        # Generate report based on type
        if report_type == 'prices':
            content = exporter.generate_price_matrix()
            filename = 'prices_matrix.xlsx'
        elif report_type == 'reviews':
            content = exporter.generate_reviews_matrix()
            filename = 'reviews_matrix.xlsx'
        elif report_type == 'insights':
            content = exporter.generate_insights_report()
            filename = 'insights.xlsx'
        else:
            content = exporter.generate_full_report()
            filename = 'full_report.xlsx'

        # Build filename with date range
        if period_from and period_to:
            date_suffix = f'_{period_from.strftime("%Y%m%d")}_{period_to.strftime("%Y%m%d")}'
            filename = filename.replace('.xlsx', f'{date_suffix}.xlsx')

        # Return response
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(
            f'Report exported: type={report_type}, period={period_from}-{period_to}, '
            f'is_own={is_own}, retailer={retailer_id}, user={request.user.username}'
        )

        return response

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None

    def _parse_is_own(self, value: str) -> bool | None:
        """Parse is_own parameter."""
        if value == '1' or value == 'true':
            return True
        elif value == '0' or value == 'false':
            return False
        return None
