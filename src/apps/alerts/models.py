"""
Alert models - rules and triggered events.
Implemented in Phase 4.
"""
from django.db import models

from apps.core.models import BaseModel
from apps.products.models import Product, Listing
from apps.retailers.models import Retailer
from apps.scraping.models import SnapshotPrice


class AlertRule(BaseModel):
    """
    Alert rule configuration.
    """

    class AlertTypeChoices(models.TextChoices):
        PRICE_INCREASE = 'price_increase', 'Рост цены'
        PRICE_DECREASE = 'price_decrease', 'Падение цены'
        NEW_NEGATIVE_REVIEW = 'new_negative_review', 'Новый негативный отзыв'
        NEW_POSITIVE_COMPETITOR = 'new_positive_competitor', 'Позитивный отзыв конкурента'
        OUT_OF_STOCK = 'out_of_stock', 'Нет в наличии'

    class ChannelChoices(models.TextChoices):
        TELEGRAM = 'telegram', 'Telegram'
        EMAIL = 'email', 'Email'

    name = models.CharField('Название', max_length=100)
    alert_type = models.CharField(
        'Тип',
        max_length=30,
        choices=AlertTypeChoices.choices,
    )
    is_active = models.BooleanField('Активно', default=True)

    # Scope (NULL = all)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alert_rules',
        verbose_name='Товар',
    )
    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alert_rules',
        verbose_name='Ретейлер',
    )

    # Thresholds
    threshold_pct = models.DecimalField(
        'Порог (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Для алертов на цену',
    )
    threshold_rating = models.PositiveSmallIntegerField(
        'Порог рейтинга',
        null=True,
        blank=True,
        help_text='Для алертов на отзывы',
    )

    # Notification settings
    channel = models.CharField(
        'Канал',
        max_length=20,
        choices=ChannelChoices.choices,
        default=ChannelChoices.TELEGRAM,
    )
    recipients = models.JSONField(
        'Получатели',
        default=list,
        help_text='["chat_id", "@username"]',
    )
    cooldown_hours = models.PositiveIntegerField(
        'Пауза (часы)',
        default=24,
        help_text='Не чаще чем раз в N часов',
    )

    class Meta:
        verbose_name = 'Правило оповещения'
        verbose_name_plural = 'Правила оповещений'
        ordering = ['name']

    def __str__(self):
        return self.name


class AlertEvent(BaseModel):
    """
    Triggered alert event.
    """

    alert_rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Правило',
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='alert_events',
        verbose_name='Листинг',
    )
    snapshot = models.ForeignKey(
        SnapshotPrice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_events',
        verbose_name='Снимок',
    )

    triggered_at = models.DateTimeField('Время срабатывания', auto_now_add=True)
    message = models.TextField('Сообщение')
    details = models.JSONField(
        'Детали',
        default=dict,
        help_text='{"old_price": 100, "new_price": 120, "pct_change": 20}',
    )

    is_delivered = models.BooleanField('Доставлено', default=False)
    delivered_at = models.DateTimeField('Время доставки', null=True, blank=True)
    delivery_error = models.TextField('Ошибка доставки', blank=True)

    class Meta:
        verbose_name = 'Событие оповещения'
        verbose_name_plural = 'События оповещений'
        ordering = ['-triggered_at']

    def __str__(self):
        return f'{self.alert_rule.name} @ {self.triggered_at}'
