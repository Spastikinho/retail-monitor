"""
Product models - products and their listings on retailers.
"""
from django.db import models

from apps.core.models import BaseModel
from apps.retailers.models import Retailer


class Product(BaseModel):
    """
    Abstract product entity (not tied to any retailer).
    A product can have multiple listings on different retailers.
    """

    class PackagingChoices(models.TextChoices):
        DOYPACK = 'doypack', 'Дой-пак'
        BOX = 'box', 'Коробка'
        BAG = 'bag', 'Пакет'
        TRAY = 'tray', 'Лоток'
        JAR = 'jar', 'Банка'
        OTHER = 'other', 'Другое'

    name = models.CharField('Название', max_length=255)
    brand = models.CharField('Бренд', max_length=100)
    is_own = models.BooleanField(
        'Наш товар',
        default=True,
        help_text='Отметьте для собственных товаров, снимите для конкурентов',
    )

    # Product attributes
    product_type = models.CharField('Тип продукта', max_length=100, blank=True)
    packaging_type = models.CharField(
        'Тип упаковки',
        max_length=20,
        choices=PackagingChoices.choices,
        blank=True,
    )
    weight_grams = models.PositiveIntegerField('Вес (г)', null=True, blank=True)
    caliber = models.CharField('Калибр', max_length=50, blank=True)
    has_pit = models.BooleanField('С косточкой', null=True, blank=True)
    variety = models.CharField('Сорт', max_length=100, blank=True)

    # Flexible attributes for product-specific fields
    extra_attrs = models.JSONField(
        'Дополнительные атрибуты',
        default=dict,
        blank=True,
        help_text='JSON с дополнительными характеристиками',
    )

    notes = models.TextField('Заметки', blank=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['brand', 'name']

    def __str__(self):
        weight = f' {self.weight_grams}г' if self.weight_grams else ''
        return f'{self.brand} - {self.name}{weight}'

    @property
    def active_listings_count(self):
        return self.listings.filter(is_active=True).count()


class Listing(BaseModel):
    """
    Product listing on a specific retailer.
    Links a product to its page on a retailer's website.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Товар',
    )
    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Ретейлер',
    )

    external_url = models.URLField('URL товара', max_length=500)
    external_id = models.CharField(
        'ID на площадке',
        max_length=100,
        blank=True,
        help_text='SKU или ID товара на площадке',
    )

    is_active = models.BooleanField('Активен', default=True)
    scrape_priority = models.PositiveSmallIntegerField(
        'Приоритет',
        default=5,
        help_text='1-10, выше = раньше в очереди',
    )

    last_scraped_at = models.DateTimeField(
        'Последний сбор',
        null=True,
        blank=True,
    )
    last_scrape_error = models.TextField('Последняя ошибка', blank=True)

    class Meta:
        verbose_name = 'Листинг'
        verbose_name_plural = 'Листинги'
        unique_together = ['product', 'retailer']
        ordering = ['-scrape_priority', 'product__name']

    def __str__(self):
        return f'{self.product.name} @ {self.retailer.name}'

    @property
    def last_price_snapshot(self):
        """Get the most recent price snapshot."""
        return self.price_snapshots.order_by('-scraped_at').first()

    @property
    def last_review_snapshot(self):
        """Get the most recent review snapshot."""
        return self.review_snapshots.order_by('-scraped_at').first()
