"""
Analytics models - LLM analysis results.
Implemented in Phase 3.
"""
from django.db import models

from apps.core.models import BaseModel
from apps.products.models import Listing


class ReviewAnalysis(BaseModel):
    """
    LLM-generated analysis of reviews for a period.
    """

    class AnalysisTypeChoices(models.TextChoices):
        MONTHLY = 'monthly', 'Ежемесячный'
        QUARTERLY = 'quarterly', 'Квартальный'

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='analyses',
        verbose_name='Листинг',
    )
    period_month = models.DateField('Период (месяц)')
    analysis_type = models.CharField(
        'Тип анализа',
        max_length=20,
        choices=AnalysisTypeChoices.choices,
        default=AnalysisTypeChoices.MONTHLY,
    )

    # Insights from negative reviews (our products)
    remove_suggestions = models.TextField('Что убрать', blank=True)
    add_packaging_suggestions = models.TextField('Добавить в упаковку', blank=True)
    add_taste_suggestions = models.TextField('Изменить во вкусе', blank=True)

    # Key themes
    key_positive_themes = models.JSONField('Позитивные темы', default=list)
    key_negative_themes = models.JSONField('Негативные темы', default=list)

    # Competitor insights
    competitor_insights = models.TextField('Инсайты конкурентов', blank=True)

    # LLM metadata
    raw_llm_response = models.JSONField('Ответ LLM', default=dict)
    model_used = models.CharField('Модель', max_length=50, blank=True)
    tokens_used = models.PositiveIntegerField('Токенов', default=0)

    generated_at = models.DateTimeField('Сгенерировано', auto_now_add=True)

    class Meta:
        verbose_name = 'Анализ отзывов'
        verbose_name_plural = 'Анализы отзывов'
        unique_together = ['listing', 'period_month', 'analysis_type']
        ordering = ['-period_month']

    def __str__(self):
        return f'Анализ {self.listing} за {self.period_month}'
