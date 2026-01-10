from django.contrib import admin

from .models import ReportRun


@admin.register(ReportRun)
class ReportRunAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'period_from', 'period_to', 'generated_by', 'generated_at', 'download_count']
    list_filter = ['report_type', 'generated_at']
    readonly_fields = ['id', 'created_at', 'updated_at', 'generated_at']
    date_hierarchy = 'generated_at'
