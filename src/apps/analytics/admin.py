from django.contrib import admin
from django.contrib import messages

from .models import ReviewAnalysis
from .tasks import generate_listing_analysis, generate_all_analyses, process_unprocessed_reviews


@admin.register(ReviewAnalysis)
class ReviewAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'listing', 'period_month', 'analysis_type',
        'has_suggestions', 'model_used', 'tokens_used', 'generated_at'
    ]
    list_filter = ['analysis_type', 'period_month', 'model_used', 'listing__product__is_own']
    search_fields = ['listing__product__name', 'listing__retailer__name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'generated_at',
        'raw_llm_response', 'model_used', 'tokens_used'
    ]
    raw_id_fields = ['listing']

    fieldsets = (
        (None, {
            'fields': ('listing', 'period_month', 'analysis_type')
        }),
        ('AI-выводы для наших товаров', {
            'fields': ('remove_suggestions', 'add_packaging_suggestions', 'add_taste_suggestions'),
            'classes': ('collapse',),
        }),
        ('Инсайты конкурентов', {
            'fields': ('competitor_insights',),
            'classes': ('collapse',),
        }),
        ('Темы', {
            'fields': ('key_positive_themes', 'key_negative_themes'),
        }),
        ('Метаданные LLM', {
            'fields': ('model_used', 'tokens_used', 'raw_llm_response'),
            'classes': ('collapse',),
        }),
        ('Системная информация', {
            'fields': ('id', 'created_at', 'updated_at', 'generated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['regenerate_analysis']

    @admin.display(boolean=True, description='Есть выводы')
    def has_suggestions(self, obj):
        return bool(
            obj.remove_suggestions or
            obj.add_packaging_suggestions or
            obj.add_taste_suggestions or
            obj.competitor_insights
        )

    @admin.action(description='Перегенерировать анализ')
    def regenerate_analysis(self, request, queryset):
        for analysis in queryset:
            # Delete existing and regenerate
            listing_id = str(analysis.listing_id)
            period = analysis.period_month.strftime('%Y-%m-%d')
            analysis.delete()
            generate_listing_analysis.delay(listing_id, period)

        self.message_user(
            request,
            f'Запущена перегенерация {queryset.count()} анализов',
            messages.SUCCESS
        )


# Custom admin actions for triggering analysis tasks
from django.contrib.admin import AdminSite


def run_all_analyses(modeladmin, request, queryset):
    """Run analysis for all listings with reviews."""
    generate_all_analyses.delay()
    modeladmin.message_user(
        request,
        'Запущена генерация анализов для всех листингов с отзывами',
        messages.SUCCESS
    )


def process_reviews_topics(modeladmin, request, queryset):
    """Process unprocessed reviews for topic extraction."""
    process_unprocessed_reviews.delay(limit=500)
    modeladmin.message_user(
        request,
        'Запущена обработка отзывов для извлечения тем (до 500)',
        messages.SUCCESS
    )


# Add these as site-wide admin actions
admin.site.add_action(run_all_analyses, 'run_all_analyses')
admin.site.add_action(process_reviews_topics, 'process_reviews_topics')
