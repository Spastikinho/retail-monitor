"""
Retailer models - stores and their session data.
"""
from django.db import models
from django.conf import settings

from cryptography.fernet import Fernet

from apps.core.models import BaseModel


class Retailer(BaseModel):
    """
    Retailer/marketplace configuration.
    Each retailer has its own connector class for scraping.
    """

    class ConnectorChoices(models.TextChoices):
        OZON = 'apps.scraping.connectors.ozon.OzonConnector', 'Ozon'
        VKUSVILL = 'apps.scraping.connectors.vkusvill.VkusvillConnector', 'ВкусВилл'
        PEREKRESTOK = 'apps.scraping.connectors.perekrestok.PerekrestokConnector', 'Перекрёсток'
        LAVKA = 'apps.scraping.connectors.lavka.LavkaConnector', 'Яндекс Лавка'

    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Код', max_length=50, unique=True)
    base_url = models.URLField('Базовый URL')
    connector_class = models.CharField(
        'Класс коннектора',
        max_length=100,
        choices=ConnectorChoices.choices,
    )
    is_active = models.BooleanField('Активен', default=True)
    requires_auth = models.BooleanField('Требует авторизации', default=False)
    default_region = models.CharField('Регион по умолчанию', max_length=50, default='moscow')
    rate_limit_rpm = models.PositiveIntegerField('Лимит запросов/мин', default=10)

    # URL patterns for parsing product URLs
    product_url_pattern = models.CharField(
        'Паттерн URL товара',
        max_length=255,
        help_text='Regex для извлечения ID товара из URL',
        blank=True,
    )

    class Meta:
        verbose_name = 'Ретейлер'
        verbose_name_plural = 'Ретейлеры'
        ordering = ['name']

    def __str__(self):
        return self.name


class RetailerSession(BaseModel):
    """
    Encrypted session data for authenticated scraping.
    Stores cookies and localStorage for browser automation.
    """

    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Ретейлер',
    )
    region_code = models.CharField('Код региона', max_length=50, default='moscow')

    # Encrypted session data
    cookies_encrypted = models.BinaryField('Cookies (зашифровано)', null=True, blank=True)
    local_storage_encrypted = models.BinaryField('LocalStorage (зашифровано)', null=True, blank=True)

    user_agent = models.CharField('User-Agent', max_length=500, blank=True)
    is_valid = models.BooleanField('Валидна', default=True)
    last_used_at = models.DateTimeField('Последнее использование', null=True, blank=True)
    expires_at = models.DateTimeField('Истекает', null=True, blank=True)
    notes = models.TextField('Заметки', blank=True)

    class Meta:
        verbose_name = 'Сессия ретейлера'
        verbose_name_plural = 'Сессии ретейлеров'
        unique_together = ['retailer', 'region_code']

    def __str__(self):
        return f'{self.retailer.name} ({self.region_code})'

    def _get_fernet(self):
        """Get Fernet instance for encryption/decryption."""
        key = settings.ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY not configured")
        return Fernet(key.encode() if isinstance(key, str) else key)

    def set_cookies(self, cookies_json: str):
        """Encrypt and store cookies."""
        fernet = self._get_fernet()
        self.cookies_encrypted = fernet.encrypt(cookies_json.encode())

    def get_cookies(self) -> str | None:
        """Decrypt and return cookies."""
        if not self.cookies_encrypted:
            return None
        fernet = self._get_fernet()
        return fernet.decrypt(bytes(self.cookies_encrypted)).decode()

    def set_local_storage(self, storage_json: str):
        """Encrypt and store localStorage."""
        fernet = self._get_fernet()
        self.local_storage_encrypted = fernet.encrypt(storage_json.encode())

    def get_local_storage(self) -> str | None:
        """Decrypt and return localStorage."""
        if not self.local_storage_encrypted:
            return None
        fernet = self._get_fernet()
        return fernet.decrypt(bytes(self.local_storage_encrypted)).decode()
