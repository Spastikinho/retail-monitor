"""
Reports models - export history.
Implemented in Phase 3.
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import BaseModel

User = get_user_model()


class ReportRun(BaseModel):
    """
    Report generation history.
    """

    class ReportTypeChoices(models.TextChoices):
        PRICE_MATRIX = 'price_matrix', 'Матрица цен'
        REVIEW_MATRIX = 'review_matrix', 'Матрица отзывов'
        INSIGHTS_MATRIX = 'insights_matrix', 'Матрица выводов'
        FULL = 'full', 'Полный отчёт'
        PRODUCT_JOURNAL = 'product_journal', 'Журнал по товару'

    report_type = models.CharField(
        'Тип отчёта',
        max_length=30,
        choices=ReportTypeChoices.choices,
    )

    period_from = models.DateField('Период с')
    period_to = models.DateField('Период по')

    filters = models.JSONField(
        'Фильтры',
        default=dict,
        blank=True,
        help_text='{"is_own": true, "retailer_id": "..."}',
    )

    file_path = models.CharField('Путь к файлу', max_length=255, blank=True)
    file_size_bytes = models.PositiveIntegerField('Размер (байт)', default=0)

    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_runs',
        verbose_name='Создал',
    )
    generated_at = models.DateTimeField('Создано', auto_now_add=True)
    download_count = models.PositiveIntegerField('Скачиваний', default=0)

    class Meta:
        verbose_name = 'Отчёт'
        verbose_name_plural = 'Отчёты'
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.get_report_type_display()} ({self.period_from} - {self.period_to})'
