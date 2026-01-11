"""
Scraping models - snapshots and sessions.
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import BaseModel
from apps.products.models import Listing
from apps.retailers.models import Retailer

User = get_user_model()


class ScrapeSession(BaseModel):
    """
    A scraping session - one run of data collection.
    Can be manual (single listing) or scheduled (all listings).
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменено'

    class TriggerChoices(models.TextChoices):
        MANUAL = 'manual', 'Вручную'
        SCHEDULED = 'scheduled', 'По расписанию'

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    trigger_type = models.CharField(
        'Тип запуска',
        max_length=20,
        choices=TriggerChoices.choices,
        default=TriggerChoices.MANUAL,
    )

    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scrape_sessions',
        verbose_name='Ретейлер',
        help_text='NULL = все ретейлеры',
    )

    started_at = models.DateTimeField('Начало', null=True, blank=True)
    finished_at = models.DateTimeField('Окончание', null=True, blank=True)

    listings_total = models.PositiveIntegerField('Всего листингов', default=0)
    listings_success = models.PositiveIntegerField('Успешно', default=0)
    listings_failed = models.PositiveIntegerField('С ошибками', default=0)

    error_log = models.TextField('Лог ошибок', blank=True)

    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scrape_sessions',
        verbose_name='Запустил',
    )

    class Meta:
        verbose_name = 'Сессия сбора'
        verbose_name_plural = 'Сессии сбора'
        ordering = ['-created_at']

    def __str__(self):
        return f'Сессия {self.created_at:%Y-%m-%d %H:%M} ({self.status})'

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None


class SnapshotPrice(BaseModel):
    """
    Price snapshot - captured price data at a point in time.
    """

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='price_snapshots',
        verbose_name='Листинг',
    )
    session = models.ForeignKey(
        ScrapeSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_snapshots',
        verbose_name='Сессия',
    )

    scraped_at = models.DateTimeField('Время сбора', auto_now_add=True)
    period_month = models.DateField(
        'Период (месяц)',
        help_text='Первый день месяца для группировки',
    )

    # Prices
    price_regular = models.DecimalField(
        'Обычная цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_promo = models.DecimalField(
        'Акционная цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_card = models.DecimalField(
        'Цена по карте',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_final = models.DecimalField(
        'Итоговая цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Минимальная из всех цен',
    )
    currency = models.CharField('Валюта', max_length=3, default='RUB')

    # Stock
    in_stock = models.BooleanField('В наличии', default=True)
    stock_quantity = models.PositiveIntegerField('Количество', null=True, blank=True)

    # Rating
    rating_avg = models.DecimalField(
        'Средний рейтинг',
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
    )
    reviews_count = models.PositiveIntegerField(
        'Кол-во отзывов',
        null=True,
        blank=True,
    )

    # Raw data for debugging
    raw_data = models.JSONField('Сырые данные', default=dict, blank=True)

    class Meta:
        verbose_name = 'Снимок цены'
        verbose_name_plural = 'Снимки цен'
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['listing', 'period_month']),
            models.Index(fields=['period_month']),
        ]

    def __str__(self):
        return f'{self.listing} @ {self.scraped_at:%Y-%m-%d}'


class SnapshotReview(BaseModel):
    """
    Aggregated review statistics snapshot for a period.
    """

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='review_snapshots',
        verbose_name='Листинг',
    )
    session = models.ForeignKey(
        ScrapeSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_snapshots',
        verbose_name='Сессия',
    )

    scraped_at = models.DateTimeField('Время сбора', auto_now_add=True)
    period_month = models.DateField('Период (месяц)')

    # Review counts by rating
    reviews_1_count = models.PositiveIntegerField('Отзывов 1*', default=0)
    reviews_2_count = models.PositiveIntegerField('Отзывов 2*', default=0)
    reviews_3_count = models.PositiveIntegerField('Отзывов 3*', default=0)
    reviews_4_count = models.PositiveIntegerField('Отзывов 4*', default=0)
    reviews_5_count = models.PositiveIntegerField('Отзывов 5*', default=0)

    # Computed field for negative reviews
    reviews_1_3_count = models.PositiveIntegerField(
        'Негативных (1-3*)',
        default=0,
        help_text='Сумма 1+2+3',
    )

    # New reviews since last scrape
    new_reviews_count = models.PositiveIntegerField(
        'Новых отзывов',
        default=0,
    )

    class Meta:
        verbose_name = 'Снимок отзывов'
        verbose_name_plural = 'Снимки отзывов'
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['listing', 'period_month']),
        ]

    def __str__(self):
        return f'{self.listing} отзывы @ {self.period_month}'

    def save(self, *args, **kwargs):
        # Auto-calculate 1-3 count
        self.reviews_1_3_count = (
            self.reviews_1_count +
            self.reviews_2_count +
            self.reviews_3_count
        )
        super().save(*args, **kwargs)


class ReviewItem(BaseModel):
    """
    Individual review from a retailer.
    """

    class SentimentChoices(models.TextChoices):
        POSITIVE = 'positive', 'Позитивный'
        NEUTRAL = 'neutral', 'Нейтральный'
        NEGATIVE = 'negative', 'Негативный'

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Листинг',
    )

    external_id = models.CharField(
        'ID отзыва',
        max_length=100,
        help_text='ID на площадке для дедупликации',
    )
    rating = models.PositiveSmallIntegerField('Рейтинг', choices=[(i, str(i)) for i in range(1, 6)])
    text = models.TextField('Текст отзыва')

    author_name = models.CharField('Автор', max_length=100, blank=True)
    pros = models.TextField('Достоинства', blank=True)
    cons = models.TextField('Недостатки', blank=True)

    published_at = models.DateField('Дата публикации', null=True, blank=True)
    scraped_at = models.DateTimeField('Время сбора', auto_now_add=True)

    # AI processing
    is_processed = models.BooleanField('Обработан', default=False)
    sentiment = models.CharField(
        'Тональность',
        max_length=20,
        choices=SentimentChoices.choices,
        blank=True,
    )
    topics = models.JSONField(
        'Темы',
        default=list,
        blank=True,
        help_text='["упаковка", "вкус", ...]',
    )

    raw_data = models.JSONField('Сырые данные', default=dict, blank=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ['listing', 'external_id']
        ordering = ['-published_at', '-scraped_at']
        indexes = [
            models.Index(fields=['listing', 'rating']),
            models.Index(fields=['is_processed']),
        ]

    def __str__(self):
        return f'{self.rating}* от {self.author_name or "Аноним"}'

    def save(self, *args, **kwargs):
        # Auto-set sentiment based on rating
        if not self.sentiment:
            if self.rating <= 3:
                self.sentiment = self.SentimentChoices.NEGATIVE
            elif self.rating == 4:
                self.sentiment = self.SentimentChoices.NEUTRAL
            else:
                self.sentiment = self.SentimentChoices.POSITIVE
        super().save(*args, **kwargs)


class ScrapeRun(BaseModel):
    """
    A batch run of scraping jobs - groups multiple ManualImports together.
    Allows tracking progress and results as a unit.
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        COMPLETED_WITH_ERRORS = 'completed_with_errors', 'Completed with errors'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='scrape_runs',
        verbose_name='User',
    )
    status = models.CharField(
        'Status',
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )

    items_total = models.PositiveIntegerField('Total items', default=0)
    items_completed = models.PositiveIntegerField('Completed', default=0)
    items_failed = models.PositiveIntegerField('Failed', default=0)

    options = models.JSONField(
        'Run options',
        default=dict,
        blank=True,
        help_text='Options passed when creating the run',
    )

    finished_at = models.DateTimeField('Finished at', null=True, blank=True)

    # Artifact storage pointer (for future S3/R2 integration)
    artifact_bucket = models.CharField(
        'Artifact bucket',
        max_length=100,
        blank=True,
        help_text='S3/R2 bucket name for raw artifacts',
    )
    artifact_prefix = models.CharField(
        'Artifact prefix',
        max_length=200,
        blank=True,
        help_text='Prefix/folder path in bucket',
    )

    class Meta:
        verbose_name = 'Scrape Run'
        verbose_name_plural = 'Scrape Runs'
        ordering = ['-created_at']

    def __str__(self):
        return f'Run {self.created_at:%Y-%m-%d %H:%M} ({self.status})'

    @property
    def progress_percent(self):
        if self.items_total == 0:
            return 0
        return int((self.items_completed + self.items_failed) / self.items_total * 100)


class MonitoringGroup(BaseModel):
    """
    Group for organizing monitored products (e.g., "My Products", "Competitor A").
    """

    class TypeChoices(models.TextChoices):
        OWN = 'own', 'Наши товары'
        COMPETITOR = 'competitor', 'Конкуренты'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='monitoring_groups',
        verbose_name='Пользователь',
    )
    name = models.CharField('Название группы', max_length=100)
    group_type = models.CharField(
        'Тип',
        max_length=20,
        choices=TypeChoices.choices,
        default=TypeChoices.COMPETITOR,
    )
    description = models.TextField('Описание', blank=True)
    color = models.CharField(
        'Цвет',
        max_length=7,
        default='#6b7280',
        help_text='HEX цвет для отображения',
    )

    class Meta:
        verbose_name = 'Группа мониторинга'
        verbose_name_plural = 'Группы мониторинга'
        ordering = ['group_type', 'name']
        unique_together = ['user', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_group_type_display()})'


class ManualImport(BaseModel):
    """
    Manual URL import for on-demand scraping.
    Allows users to paste product URLs and get immediate analysis.
    Enhanced for competitive intelligence and monthly monitoring.
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PROCESSING = 'processing', 'Обрабатывается'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'

    class ProductTypeChoices(models.TextChoices):
        OWN = 'own', 'Наш товар'
        COMPETITOR = 'competitor', 'Конкурент'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manual_imports',
        verbose_name='Пользователь',
    )
    url = models.URLField('URL товара', max_length=2000)
    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_imports',
        verbose_name='Ретейлер',
        help_text='Определяется автоматически из URL',
    )

    # Categorization for competitive analysis
    product_type = models.CharField(
        'Тип товара',
        max_length=20,
        choices=ProductTypeChoices.choices,
        default=ProductTypeChoices.COMPETITOR,
    )
    group = models.ForeignKey(
        MonitoringGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imports',
        verbose_name='Группа',
    )
    run = models.ForeignKey(
        ScrapeRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imports',
        verbose_name='Run',
        help_text='Batch run this import belongs to',
    )
    custom_name = models.CharField(
        'Своё название',
        max_length=200,
        blank=True,
        help_text='Ваше название для товара (для отчётов)',
    )
    notes = models.TextField('Заметки', blank=True)

    # Tracking for monthly monitoring
    monitoring_period = models.DateField(
        'Период мониторинга',
        null=True,
        blank=True,
        help_text='Месяц мониторинга (первый день месяца)',
    )
    is_recurring = models.BooleanField(
        'Повторять ежемесячно',
        default=False,
        help_text='Автоматически собирать данные каждый месяц',
    )

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )

    # Results
    product_title = models.CharField('Название товара', max_length=500, blank=True)
    price_regular = models.DecimalField(
        'Обычная цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_promo = models.DecimalField(
        'Акционная цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_final = models.DecimalField(
        'Итоговая цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rating = models.DecimalField(
        'Рейтинг',
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
    )
    reviews_count = models.PositiveIntegerField('Кол-во отзывов', null=True, blank=True)
    in_stock = models.BooleanField('В наличии', null=True, blank=True)

    # Price change tracking
    price_previous = models.DecimalField(
        'Предыдущая цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_change = models.DecimalField(
        'Изменение цены',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Разница с предыдущим периодом',
    )
    price_change_pct = models.DecimalField(
        'Изменение цены %',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Reviews data
    reviews_data = models.JSONField(
        'Данные отзывов',
        default=list,
        blank=True,
        help_text='Список отзывов в формате JSON',
    )

    # Analyzed review insights
    review_insights = models.JSONField(
        'Инсайты из отзывов',
        default=dict,
        blank=True,
        help_text='Анализ отзывов: темы, настроения, ключевые слова',
    )

    # Review statistics
    reviews_positive_count = models.PositiveIntegerField('Положительных отзывов', default=0)
    reviews_negative_count = models.PositiveIntegerField('Отрицательных отзывов', default=0)
    reviews_neutral_count = models.PositiveIntegerField('Нейтральных отзывов', default=0)

    error_message = models.TextField('Сообщение об ошибке', blank=True)
    raw_data = models.JSONField('Сырые данные', default=dict, blank=True)

    processed_at = models.DateTimeField('Время обработки', null=True, blank=True)

    class Meta:
        verbose_name = 'Ручной импорт'
        verbose_name_plural = 'Ручные импорты'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'product_type']),
            models.Index(fields=['user', 'monitoring_period']),
            models.Index(fields=['url']),
        ]

    def __str__(self):
        name = self.custom_name or self.product_title or self.url[:50]
        return f'{name} ({self.status})'

    @property
    def display_name(self):
        """Return the best available name for display."""
        return self.custom_name or self.product_title or self.url[:60]

    def detect_retailer(self):
        """Detect retailer from URL."""
        url_lower = self.url.lower()
        retailer_patterns = {
            'ozon': ['ozon.ru'],
            'wildberries': ['wildberries.ru', 'wb.ru'],
            'perekrestok': ['perekrestok.ru'],
            'vkusvill': ['vkusvill.ru'],
            'lavka': ['lavka.yandex.ru', 'eda.yandex.ru/lavka'],
        }

        for slug, patterns in retailer_patterns.items():
            for pattern in patterns:
                if pattern in url_lower:
                    try:
                        return Retailer.objects.get(slug=slug)
                    except Retailer.DoesNotExist:
                        return None
        return None

    def calculate_price_change(self):
        """Calculate price change from previous period."""
        if not self.price_final or not self.monitoring_period:
            return

        # Find previous import for same URL
        previous = ManualImport.objects.filter(
            user=self.user,
            url=self.url,
            status=self.StatusChoices.COMPLETED,
            monitoring_period__lt=self.monitoring_period,
        ).order_by('-monitoring_period').first()

        if previous and previous.price_final:
            self.price_previous = previous.price_final
            self.price_change = self.price_final - previous.price_final
            if previous.price_final > 0:
                self.price_change_pct = (
                    (self.price_final - previous.price_final) /
                    previous.price_final * 100
                )

    def analyze_reviews(self):
        """Analyze reviews and extract insights."""
        if not self.reviews_data:
            return

        positive = 0
        negative = 0
        neutral = 0

        # Topic keywords
        taste_keywords = ['вкус', 'вкусн', 'невкусн', 'сладк', 'кисл', 'горьк', 'солён']
        packaging_keywords = ['упаковк', 'коробк', 'пакет', 'открыв', 'закрыв', 'хранен']
        quality_keywords = ['качеств', 'свеж', 'испорч', 'плесен', 'срок']
        price_keywords = ['цен', 'дорог', 'дёшев', 'стоим', 'скидк']

        topics = {
            'taste': {'mentions': 0, 'positive': 0, 'negative': 0, 'samples': []},
            'packaging': {'mentions': 0, 'positive': 0, 'negative': 0, 'samples': []},
            'quality': {'mentions': 0, 'positive': 0, 'negative': 0, 'samples': []},
            'price': {'mentions': 0, 'positive': 0, 'negative': 0, 'samples': []},
        }

        for review in self.reviews_data:
            rating = review.get('rating', 3)
            text = (review.get('text', '') + ' ' +
                   review.get('pros', '') + ' ' +
                   review.get('cons', '')).lower()

            # Count sentiment
            if rating >= 4:
                positive += 1
                sentiment = 'positive'
            elif rating <= 2:
                negative += 1
                sentiment = 'negative'
            else:
                neutral += 1
                sentiment = 'neutral'

            # Extract topics
            for kw in taste_keywords:
                if kw in text:
                    topics['taste']['mentions'] += 1
                    topics['taste'][sentiment] += 1
                    if len(topics['taste']['samples']) < 3:
                        topics['taste']['samples'].append(text[:200])
                    break

            for kw in packaging_keywords:
                if kw in text:
                    topics['packaging']['mentions'] += 1
                    topics['packaging'][sentiment] += 1
                    if len(topics['packaging']['samples']) < 3:
                        topics['packaging']['samples'].append(text[:200])
                    break

            for kw in quality_keywords:
                if kw in text:
                    topics['quality']['mentions'] += 1
                    topics['quality'][sentiment] += 1
                    if len(topics['quality']['samples']) < 3:
                        topics['quality']['samples'].append(text[:200])
                    break

            for kw in price_keywords:
                if kw in text:
                    topics['price']['mentions'] += 1
                    topics['price'][sentiment] += 1
                    if len(topics['price']['samples']) < 3:
                        topics['price']['samples'].append(text[:200])
                    break

        self.reviews_positive_count = positive
        self.reviews_negative_count = negative
        self.reviews_neutral_count = neutral
        self.review_insights = {
            'topics': topics,
            'total_analyzed': len(self.reviews_data),
            'sentiment_summary': {
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
            }
        }

    def save(self, *args, **kwargs):
        # Auto-detect retailer if not set
        if not self.retailer:
            self.retailer = self.detect_retailer()

        # Set monitoring period if not set
        if not self.monitoring_period:
            from django.utils import timezone
            today = timezone.now().date()
            self.monitoring_period = today.replace(day=1)

        super().save(*args, **kwargs)
